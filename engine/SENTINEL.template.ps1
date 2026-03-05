###############################################################
#  SENTINEL.template.ps1 - Adam Framework Watchdog
#  Version: 1.1.0
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
#    2. Run once manually to verify it works
#    3. Register as a Windows Task Scheduler job for auto-start on login
#    4. See docs/SETUP.md for Task Scheduler instructions
#
#  REQUIREMENTS:
#    - Windows PowerShell 5.1+
#    - OpenClaw installed
#    - Python 3.10+ (if using Kokoro TTS)
###############################################################

# ── CONFIGURE THESE FOR YOUR SYSTEM ─────────────────────────
$VAULT_PATH   = "C:\YOUR_VAULT_PATH"           # e.g. C:\MyAIVault
$OPENCLAW_DIR = "$env:USERPROFILE\.openclaw"   # Usually fine as-is
$GATEWAY_CMD  = "$OPENCLAW_DIR\gateway.cmd"
$LOG_FILE     = "$OPENCLAW_DIR\sentinel.log"
$PYTHON_EXE   = "python"                       # Override if needed: C:\Python312\python.exe
# ─────────────────────────────────────────────────────────────

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line
}

function Start-Gateway {
    $proc = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList "/c `"$GATEWAY_CMD`"" `
        -WindowStyle Normal `
        -PassThru
    Write-Log "Gateway started - PID $($proc.Id)"
    return $proc
}

function Invoke-CoherenceCheck {
    $script = "$VAULT_PATH\tools\coherence_monitor.py"
    if (-not (Test-Path $script)) { return }
    try {
        $result = & $PYTHON_EXE $script --vault-path "$VAULT_PATH" 2>&1
        $exit   = $LASTEXITCODE
        if ($exit -eq 1) {
            Write-Log "Coherence monitor: drift detected — re-anchor pending."
        } elseif ($exit -eq 0) {
            Write-Log "Coherence monitor: session coherent."
        } else {
            Write-Log "Coherence monitor: error (exit $exit) — skipping."
        }
    } catch {
        Write-Log "Coherence monitor: exception — $($_.Exception.Message)"
    }
}

function Invoke-ReAnchor {
    $pendingFile = "$VAULT_PATH\workspace\reanchor_pending.json"
    if (-not (Test-Path $pendingFile)) { return }
    try {
        $pending = Get-Content $pendingFile -Raw | ConvertFrom-Json
        if ($pending.consumed -eq $false -and $pending.content) {
            $bootContext = "$VAULT_PATH\workspace\BOOT_CONTEXT.md"
            $section = "`n`n---`n`n## Re-Anchor Injection ($($pending.timestamp))`n`n$($pending.content)"
            Add-Content -Path $bootContext -Value $section -Encoding UTF8
            $pending.consumed = $true
            $pending | ConvertTo-Json | Set-Content $pendingFile -Encoding UTF8
            Write-Log "Re-anchor injected into BOOT_CONTEXT.md."
        }
    } catch {
        Write-Log "Re-anchor failed (non-fatal): $($_.Exception.Message)"
    }
}

# ── 1. KILL STALE INSTANCES ──────────────────────────────────
Write-Log "Sentinel rising. Clearing stale processes..."
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2
Write-Log "Stale processes cleared."

# ── 2. DATE INJECTION ────────────────────────────────────────
# This is critical. LLMs hallucinate dates from training data.
# Writing the real date to a file and telling the AI to read it
# is the most reliable solution. Dead simple. Works perfectly.
$todayISO  = Get-Date -Format "yyyy-MM-dd"
$todayFull = Get-Date -Format "dddd, MMMM dd, yyyy"
$dateFile  = "$VAULT_PATH\workspace\TODAY.md"
$dateContent = "# Authoritative Date`n`nToday is **$todayISO** ($todayFull)`n`nThis file is written by SENTINEL at every gateway start. It is the ONLY authoritative date source. Never guess the date — always read this file first."
Set-Content -Path $dateFile -Value $dateContent -Encoding UTF8
Write-Log "Date injected: $todayISO"

# ── 3. SLEEP CYCLE (runs before gateway, Markdown + neural only) ─────────────
# Merges unprocessed daily logs into CORE_MEMORY.md and incrementally
# updates the neural graph. Only runs if more than 6 hours since last run.
# Vector reindex happens AFTER the gateway is healthy (Block 2 below).
$reconcileScript = "$VAULT_PATH\tools\reconcile_memory.py"
$reconcileState  = "$VAULT_PATH\workspace\memory\_reconcile_state.json"
$runReconcile    = $false

if (Test-Path $reconcileScript) {
    if (Test-Path $reconcileState) {
        try {
            $state      = Get-Content $reconcileState -Raw | ConvertFrom-Json
            $lastRun    = [datetime]::Parse($state.last_reconcile_run)
            $hoursSince = ([datetime]::Now - $lastRun).TotalHours
            if ($hoursSince -gt 6) { $runReconcile = $true }
        } catch {
            $runReconcile = $true
        }
    } else {
        $runReconcile = $true
    }

    if ($runReconcile) {
        Write-Log "Sleep cycle: running reconcile_memory.py..."
        $geminiKey = ""
        try {
            $ocCfg     = Get-Content "$OPENCLAW_DIR\openclaw.json" -Raw | ConvertFrom-Json
            $geminiKey = $ocCfg.env.GEMINI_API_KEY
        } catch { }

        if ($geminiKey) {
            $result = & $PYTHON_EXE "$reconcileScript" --vault-path "$VAULT_PATH" --api-key "$geminiKey" 2>&1 | Out-String
            Write-Log "Sleep cycle complete."
        } else {
            Write-Log "Sleep cycle skipped: GEMINI_API_KEY not found in openclaw.json."
        }
    } else {
        Write-Log "Sleep cycle: skipped (ran less than 6 hours ago)."
    }
} else {
    Write-Log "Sleep cycle: reconcile_memory.py not found — skipping."
}

# ── 4. BOOT CONTEXT COMPILATION ──────────────────────────────
# Reads your identity files and compiles them into BOOT_CONTEXT.md
# OpenClaw injects this file automatically on session start.
# This is how your AI knows who it is before it says a single word.
Write-Log "Compiling BOOT_CONTEXT.md..."
try {
    $coreMemory    = Get-Content "$VAULT_PATH\CORE_MEMORY.md" -Raw -Encoding UTF8
    $activeContext = ""
    if (Test-Path "$VAULT_PATH\workspace\active-context.md") {
        $activeContext = Get-Content "$VAULT_PATH\workspace\active-context.md" -Raw -Encoding UTF8
    }
    $bootPayload  = "# BOOT CONTEXT — Compiled by SENTINEL`n"
    $bootPayload += "> Auto-generated before each session. Do not edit manually.`n`n---`n`n"
    $bootPayload += "## Core Memory`n`n" + $coreMemory
    if ($activeContext) {
        $bootPayload += "`n`n---`n`n## Active Context`n`n" + $activeContext
    }
    Set-Content -Path "$VAULT_PATH\workspace\BOOT_CONTEXT.md" -Value $bootPayload -Encoding UTF8
    Write-Log "BOOT_CONTEXT.md compiled successfully."
} catch {
    Write-Log "WARNING: BOOT_CONTEXT.md compilation failed (non-fatal): $($_.Exception.Message)"
}

# ── 5. LAUNCH GATEWAY ────────────────────────────────────────
Write-Log "Launching OpenClaw Gateway..."
$gateway = Start-Gateway
Write-Log "Gateway LIVE on port 18789."

Write-Log "SENTINEL ACTIVE — Watchdog loop starting. Gateway check every 30s. Coherence monitor every 5 min."

# ── 7. VECTOR REINDEX (after gateway confirmed healthy) ──────
# This fires only if the sleep cycle ran this session.
# The gateway MUST be live before we trigger a reindex — that's why
# this block is here and not in reconcile_memory.py.
if ($runReconcile) {
    Write-Log "Waiting for gateway to be healthy before vector reindex..."
    $healthy  = $false
    $attempts = 0
    while (-not $healthy -and $attempts -lt 20) {
        Start-Sleep 3
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:18789/health" -TimeoutSec 5 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) { $healthy = $true }
        } catch { }
        $attempts++
    }

    if ($healthy) {
        try {
            # OpenClaw does not expose a REST reindex endpoint.
            # The correct trigger is the CLI: openclaw memory index
            $reindexResult = & openclaw memory index --agent main 2>&1 | Out-String
            Write-Log "Vector reindex triggered successfully."
        } catch {
            Write-Log "Vector reindex failed (non-fatal): $($_.Exception.Message)"
        }
    } else {
        Write-Log "Gateway not healthy after 60s — vector reindex skipped this cycle."
    }
}

# ── 8. WATCHDOG LOOP ─────────────────────────────────────────
# Every 30 seconds: check gateway alive, restart if dead.
# Every 10 ticks (5 minutes): run Layer 5 coherence check.
# Your AI should never be down for more than 30 seconds.
$coherenceCounter = 0
while ($true) {
    Start-Sleep 30
    $coherenceCounter++

    $nodeAlive = Get-Process -Id $gateway.Id -ErrorAction SilentlyContinue
    if (-not $nodeAlive) {
        Write-Log "WARNING: Gateway process died. Restarting..."
        $gateway = Start-Gateway
        Write-Log "Gateway restarted - PID $($gateway.Id)"
    }

    if ($coherenceCounter -ge 10) {
        $coherenceCounter = 0
        Invoke-ReAnchor
        Invoke-CoherenceCheck
    }
}
