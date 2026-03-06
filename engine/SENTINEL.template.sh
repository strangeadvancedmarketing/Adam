#!/usr/bin/env bash
###############################################################
#  SENTINEL.template.sh — Adam Framework Watchdog (Linux/macOS)
#  Version: 1.0.0
#  Bash port of SENTINEL.template.ps1
#
#  WHAT THIS DOES:
#    1. Kills stale processes from previous sessions
#    2. Writes the authoritative date to your Vault (TODAY.md)
#    3. Runs sleep cycle reconciliation if >6 hours since last run
#    4. Compiles BOOT_CONTEXT.md — deterministic identity injection
#    5. Launches OpenClaw Gateway
#    6. Vector reindex after health check (if reconcile ran)
#    7. WATCHDOG LOOP — monitors gateway, auto-restarts if it dies
#                     — runs Layer 5 coherence check every 5 minutes
#
#  SETUP:
#    1. Replace all YOUR_* variables below with your actual paths
#    2. chmod +x SENTINEL.sh && run once manually to verify
#    3. Register as a launchd agent (macOS) or systemd service / cron (Linux)
#       for auto-start on login — see docs/SETUP.md
#
#  REQUIREMENTS:
#    - bash 4.0+ (macOS ships bash 3.2 — install via Homebrew: brew install bash)
#    - OpenClaw installed and 'openclaw' in PATH
#    - Python 3.10+
#    - jq  (brew install jq  /  sudo apt install jq)
#    - curl
###############################################################

# ── CONFIGURE THESE FOR YOUR SYSTEM ─────────────────────────
VAULT_PATH="$HOME/YOUR_VAULT_PATH"          # e.g. /home/user/MyAIVault
OPENCLAW_DIR="$HOME/.openclaw"              # Usually fine as-is
GATEWAY_CMD="$OPENCLAW_DIR/gateway.sh"      # Adjust if openclaw uses a different launcher
LOG_FILE="$OPENCLAW_DIR/sentinel.log"
PYTHON_EXE="python3"                        # Override if needed: /usr/bin/python3
# ─────────────────────────────────────────────────────────────

# ── HELPERS ──────────────────────────────────────────────────

write_log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    local line="[$ts] $1"
    echo "$line"
    echo "$line" >> "$LOG_FILE"
}

start_gateway() {
    # Launch gateway in background, capture PID
    openclaw start >> "$LOG_FILE" 2>&1 &
    GATEWAY_PID=$!
    write_log "Gateway started — PID $GATEWAY_PID"
}

invoke_coherence_check() {
    local script="$VAULT_PATH/tools/coherence_monitor.py"
    [[ ! -f "$script" ]] && return
    "$PYTHON_EXE" "$script" --vault-path "$VAULT_PATH" >> "$LOG_FILE" 2>&1
    local exit_code=$?
    if   [[ $exit_code -eq 1 ]]; then write_log "Coherence monitor: drift detected — re-anchor pending."
    elif [[ $exit_code -eq 0 ]]; then write_log "Coherence monitor: session coherent."
    else                               write_log "Coherence monitor: error (exit $exit_code) — skipping."
    fi
}

invoke_reanchor() {
    local pending_file="$VAULT_PATH/workspace/reanchor_pending.json"
    [[ ! -f "$pending_file" ]] && return

    # Check consumed flag
    local consumed
    consumed=$(jq -r '.consumed' "$pending_file" 2>/dev/null)
    [[ "$consumed" == "true" ]] && return

    local content
    content=$(jq -r '.content // empty' "$pending_file" 2>/dev/null)
    [[ -z "$content" ]] && return

    local timestamp
    timestamp=$(jq -r '.timestamp // "unknown"' "$pending_file" 2>/dev/null)

    local boot_context="$VAULT_PATH/workspace/BOOT_CONTEXT.md"
    {
        printf '

---

'
        printf '## Re-Anchor Injection (%s)

' "$timestamp"
        printf '%s
' "$content"
    } >> "$boot_context"

    # Mark consumed
    local tmp
    tmp=$(mktemp)
    jq '.consumed = true' "$pending_file" > "$tmp" && mv "$tmp" "$pending_file"
    write_log "Re-anchor injected into BOOT_CONTEXT.md."
}

# ── 1. KILL STALE INSTANCES ──────────────────────────────────
write_log "Sentinel rising. Clearing stale processes..."
pkill -f "openclaw" 2>/dev/null
pkill -f "gateway"  2>/dev/null
sleep 2
write_log "Stale processes cleared."

# ── 2. DATE INJECTION ────────────────────────────────────────
# LLMs hallucinate dates from training data.
# Writing the real date to a file and telling the AI to read it
# is the most reliable fix. Dead simple. Works perfectly.
TODAY_ISO=$(date '+%Y-%m-%d')
TODAY_FULL=$(date '+%A, %B %d, %Y')
DATE_FILE="$VAULT_PATH/workspace/TODAY.md"

cat > "$DATE_FILE" << EOF
# Authoritative Date

Today is **$TODAY_ISO** ($TODAY_FULL)

This file is written by SENTINEL at every gateway start. It is the ONLY authoritative date source. Never guess the date — always read this file first.
EOF

write_log "Date injected: $TODAY_ISO"

# ── 3. SLEEP CYCLE ───────────────────────────────────────────
# Merges unprocessed daily logs into CORE_MEMORY.md and
# incrementally updates the neural graph.
# Only runs if more than 6 hours since last run.
# Vector reindex happens AFTER the gateway is healthy (Block 6).
RECONCILE_SCRIPT="$VAULT_PATH/tools/reconcile_memory.py"
RECONCILE_STATE="$VAULT_PATH/workspace/memory/_reconcile_state.json"
RUN_RECONCILE=false

if [[ -f "$RECONCILE_SCRIPT" ]]; then
    if [[ -f "$RECONCILE_STATE" ]]; then
        LAST_RUN=$(jq -r '.last_reconcile_run // empty' "$RECONCILE_STATE" 2>/dev/null)
        if [[ -n "$LAST_RUN" ]]; then
            # Cross-platform epoch seconds
            if date -d "$LAST_RUN" '+%s' &>/dev/null 2>&1; then
                # GNU date (Linux)
                LAST_EPOCH=$(date -d "$LAST_RUN" '+%s' 2>/dev/null)
            else
                # BSD date (macOS)
                LAST_EPOCH=$(date -j -f '%Y-%m-%dT%H:%M:%S' "${LAST_RUN%%.*}" '+%s' 2>/dev/null)
            fi
            NOW_EPOCH=$(date '+%s')
            HOURS_SINCE=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))
            [[ $HOURS_SINCE -gt 6 ]] && RUN_RECONCILE=true
        else
            RUN_RECONCILE=true
        fi
    else
        RUN_RECONCILE=true
    fi

    if [[ "$RUN_RECONCILE" == "true" ]]; then
        write_log "Sleep cycle: running reconcile_memory.py..."
        GEMINI_KEY=$(jq -r '.env.GEMINI_API_KEY // empty' "$OPENCLAW_DIR/openclaw.json" 2>/dev/null)
        if [[ -n "$GEMINI_KEY" ]]; then
            "$PYTHON_EXE" "$RECONCILE_SCRIPT" \
                --vault-path "$VAULT_PATH" \
                --api-key "$GEMINI_KEY" \
                >> "$LOG_FILE" 2>&1
            write_log "Sleep cycle complete."
        else
            write_log "Sleep cycle skipped: GEMINI_API_KEY not found in openclaw.json."
        fi
    else
        write_log "Sleep cycle: skipped (ran less than 6 hours ago)."
    fi
else
    write_log "Sleep cycle: reconcile_memory.py not found — skipping."
fi

# ── 4. BOOT CONTEXT COMPILATION ──────────────────────────────
# Reads your identity files and compiles them into BOOT_CONTEXT.md.
# OpenClaw injects this file automatically on session start.
# This is how your AI knows who it is before it says a single word.
write_log "Compiling BOOT_CONTEXT.md..."
BOOT_CONTEXT_FILE="$VAULT_PATH/workspace/BOOT_CONTEXT.md"
CORE_MEMORY_FILE="$VAULT_PATH/CORE_MEMORY.md"
ACTIVE_CONTEXT_FILE="$VAULT_PATH/workspace/active-context.md"

if [[ -f "$CORE_MEMORY_FILE" ]]; then
    {
        printf '# BOOT CONTEXT — Compiled by SENTINEL
'
        printf '> Auto-generated before each session. Do not edit manually.

---

'
        printf '## Core Memory

'
        cat "$CORE_MEMORY_FILE"
        if [[ -f "$ACTIVE_CONTEXT_FILE" ]]; then
            printf '

---

## Active Context

'
            cat "$ACTIVE_CONTEXT_FILE"
        fi
    } > "$BOOT_CONTEXT_FILE"
    write_log "BOOT_CONTEXT.md compiled successfully."
else
    write_log "WARNING: CORE_MEMORY.md not found at $CORE_MEMORY_FILE — BOOT_CONTEXT.md not compiled."
fi

# ── 5. LAUNCH GATEWAY ────────────────────────────────────────
write_log "Launching OpenClaw Gateway..."
start_gateway
write_log "Gateway LIVE on port 18789."
write_log "SENTINEL ACTIVE — Watchdog loop starting. Gateway check every 30s. Coherence monitor every 5 min."

# ── 6. VECTOR REINDEX (after gateway confirmed healthy) ──────
# Only fires if the sleep cycle ran this session.
# Gateway MUST be live before triggering reindex.
if [[ "$RUN_RECONCILE" == "true" ]]; then
    write_log "Waiting for gateway to be healthy before vector reindex..."
    HEALTHY=false
    ATTEMPTS=0
    while [[ "$HEALTHY" == "false" && $ATTEMPTS -lt 20 ]]; do
        sleep 3
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time 5 "http://localhost:18789/health" 2>/dev/null)
        [[ "$HTTP_CODE" == "200" ]] && HEALTHY=true
        (( ATTEMPTS++ ))
    done

    if [[ "$HEALTHY" == "true" ]]; then
        if openclaw memory index --agent main >> "$LOG_FILE" 2>&1; then
            write_log "Vector reindex triggered successfully."
        else
            write_log "Vector reindex failed (non-fatal)."
        fi
    else
        write_log "Gateway not healthy after 60s — vector reindex skipped this cycle."
    fi
fi

# ── 7. WATCHDOG LOOP ─────────────────────────────────────────
# Every 30 seconds: check gateway alive, restart if dead.
# Every 10 ticks (5 minutes): run Layer 5 coherence check.
# Your AI should never be down for more than 30 seconds.
COHERENCE_COUNTER=0

while true; do
    sleep 30
    (( COHERENCE_COUNTER++ ))

    # Check if gateway process is still alive
    if ! kill -0 "$GATEWAY_PID" 2>/dev/null; then
        write_log "WARNING: Gateway process died. Restarting..."
        start_gateway
        write_log "Gateway restarted — PID $GATEWAY_PID"
    fi

    # Coherence check every 5 minutes (10 × 30s ticks)
    if [[ $COHERENCE_COUNTER -ge 10 ]]; then
        COHERENCE_COUNTER=0
        invoke_reanchor
        invoke_coherence_check
    fi
done
