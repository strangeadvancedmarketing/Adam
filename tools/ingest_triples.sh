#!/usr/bin/env bash
# Adam Framework — Ingest Triples (Step 2 of 2)
# Linux/macOS bash port of ingest_triples.ps1
#
# Loads extracted facts from legacy_importer.py into your neural memory graph.
#
# Prerequisites:
#   - neural-memory MCP server running (listed in mcporter.json)
#   - mcporter installed and in PATH
#   - extracted_triples.json exists (run legacy_importer.py first)
#   - jq installed (brew install jq / sudo apt install jq)
#
# Usage:
#   ./ingest_triples.sh --vault-path /path/to/vault
#   ./ingest_triples.sh --vault-path /path/to/vault --dry-run
#   ./ingest_triples.sh --vault-path /path/to/vault --start-at 150
#
# Options:
#   --vault-path   Path to your Vault directory (required)
#   --dry-run      Show what would be ingested without calling mcporter
#   --start-at N   Resume from a specific fact number (0-based)
#   --delay-ms N   Milliseconds between calls (default: 80)

set -euo pipefail

# ── DEFAULTS ──────────────────────────────────────────────────────────────────
VAULT_PATH=""
DRY_RUN=false
START_AT=0
DELAY_MS=80

# ── ARG PARSING ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vault-path)  VAULT_PATH="$2"; shift 2 ;;
        --dry-run)     DRY_RUN=true;    shift   ;;
        --start-at)    START_AT="$2";   shift 2 ;;
        --delay-ms)    DELAY_MS="$2";   shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1  ;;
    esac
done

if [[ -z "$VAULT_PATH" ]]; then
    echo "ERROR: --vault-path is required."
    echo "Usage: ./ingest_triples.sh --vault-path /path/to/vault"
    exit 1
fi

# ── PATHS ─────────────────────────────────────────────────────────────────────
TRIPLES_PATH="$VAULT_PATH/imports/extracted_triples.json"
LOG_PATH="$VAULT_PATH/imports/ingest_log.txt"

# ── COLOR HELPERS ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; GRAY='\033[0;37m'; WHITE='\033[1;37m'
DKGRAY='\033[2;37m'; DKRED='\033[2;31m'; NC='\033[0m'

cecho() { echo -e "${1}${2}${NC}"; }

# ── PREFLIGHT ─────────────────────────────────────────────────────────────────
echo ""
cecho "$CYAN" "=== ADAM FRAMEWORK — NEURAL MEMORY INGEST ==="
echo ""

if [[ ! -f "$TRIPLES_PATH" ]]; then
    cecho "$RED" "ERROR: extracted_triples.json not found at:"
    cecho "$RED" "  $TRIPLES_PATH"
    echo ""
    cecho "$YELLOW" "Run legacy_importer.py first to generate this file."
    exit 1
fi

if ! command -v mcporter &>/dev/null; then
    cecho "$RED" "ERROR: mcporter not found in PATH."
    cecho "$YELLOW" "Make sure mcporter is installed and your OpenClaw gateway is running."
    exit 1
fi

if ! command -v jq &>/dev/null; then
    cecho "$RED" "ERROR: jq not found. Install it first:"
    cecho "$YELLOW" "  macOS:  brew install jq"
    cecho "$YELLOW" "  Linux:  sudo apt install jq"
    exit 1
fi

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
cecho "$GRAY" "Loading $TRIPLES_PATH..."

TOTAL=$(jq '.facts | length' "$TRIPLES_PATH")

if [[ "$TOTAL" -eq 0 ]]; then
    cecho "$YELLOW" "No facts found in extracted_triples.json. Nothing to ingest."
    exit 0
fi

SOURCE=$(jq -r '._meta.source // "unknown"'    "$TRIPLES_PATH")
GENDATE=$(jq -r '._meta.generated // "unknown"' "$TRIPLES_PATH")
USERNAME=$(jq -r '._meta.user_name // "unknown"' "$TRIPLES_PATH")

cecho "$GRAY" "  Source:    $SOURCE"
cecho "$GRAY" "  Extracted: $GENDATE"
cecho "$GRAY" "  User name: $USERNAME"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    cecho "$YELLOW" "DRY RUN MODE — no mcporter calls will be made"
    echo ""
fi

REMAINING=$(( TOTAL - START_AT ))
EST_MINUTES=$(( REMAINING * (DELAY_MS + 4350) / 60000 ))
[[ $EST_MINUTES -lt 1 ]] && EST_MINUTES=1

cecho "$WHITE" "Facts to ingest: $REMAINING of $TOTAL"
[[ $START_AT -gt 0 ]] && cecho "$YELLOW" "Resuming from:   fact #$(( START_AT + 1 ))"
cecho "$WHITE" "Estimated time:  ~${EST_MINUTES} minutes"
cecho "$GRAY"  "Delay per call:  ${DELAY_MS}ms"
echo ""
cecho "$GRAY" "The ingest runs in the background. You can use your AI normally."
cecho "$GRAY" "Do not close this window until complete."
echo ""

# ── LOG HEADER ────────────────────────────────────────────────────────────────
RUN_START=$(date '+%s')
RUN_START_STR=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p "$(dirname "$LOG_PATH")"

cat >> "$LOG_PATH" << EOF
=== Ingest Run: $RUN_START_STR ===
Source: $TRIPLES_PATH
Total facts: $TOTAL
Starting at: $START_AT
Dry run: $DRY_RUN
EOF

# ── INGEST LOOP ───────────────────────────────────────────────────────────────
SUCCESS=0
FAIL=0
SKIP=0
declare -a ERRORS=()

for (( i=START_AT; i<TOTAL; i++ )); do
    TRIPLE=$(jq -c ".facts[$i]" "$TRIPLES_PATH")

    # Support both array format [s,p,o] and object format {subject,predicate,object}
    if echo "$TRIPLE" | jq -e 'type == "array"' &>/dev/null; then
        SUBJ=$(echo "$TRIPLE" | jq -r '.[0] // ""')
        PRED=$(echo "$TRIPLE" | jq -r '.[1] // ""')
        OBJ=$(echo "$TRIPLE"  | jq -r '.[2] // ""')
    else
        SUBJ=$(echo "$TRIPLE" | jq -r '.subject // ""')
        PRED=$(echo "$TRIPLE" | jq -r '.predicate // ""')
        OBJ=$(echo "$TRIPLE"  | jq -r '.object // ""')
    fi

    # Skip empty or too-short triples
    if [[ -z "$SUBJ" || -z "$OBJ" || ${#OBJ} -lt 3 ]]; then
        (( SKIP++ )) || true
        continue
    fi

    CONTENT="$SUBJ - $PRED - $OBJ"

    # Escape single quotes for mcporter call syntax
    ESCAPED="${CONTENT//\'/\'\'}"
    # Remove pipe characters that break shell parsing
    ESCAPED="${ESCAPED//|/ }"

    CMD="neural-memory.nmem_remember(content: '${ESCAPED}', type: 'fact', priority: 5, tags: ['legacy_import', 'ai_export'])"
    FACT_NUM=$(( i + 1 ))
    PREVIEW="${CONTENT:0:70}"

    if [[ "$DRY_RUN" == "true" ]]; then
        cecho "$DKGRAY" "  [DRY RUN] $FACT_NUM/$TOTAL — $PREVIEW"
        (( SUCCESS++ )) || true
    else
        RESULT=$(mcporter call "$CMD" 2>&1 || true)

        if echo "$RESULT" | grep -qE '"success":\s*true|"stored"|"id"'; then
            (( SUCCESS++ )) || true
            if (( SUCCESS % 50 == 0 )); then
                NOW=$(date '+%s')
                ELAPSED_MIN=$(( (NOW - RUN_START) / 60 ))
                [[ $ELAPSED_MIN -eq 0 ]] && ELAPSED_MIN=1
                RATE=$(( SUCCESS / ELAPSED_MIN ))
                PCT=$(( (i + 1) * 100 / TOTAL ))
                cecho "$GREEN" "  [$SUCCESS/$TOTAL — $PCT%] $RATE facts/min"
            fi
        else
            (( FAIL++ )) || true
            ERR_MSG="FAIL [$FACT_NUM]: ${CONTENT:0:60}"
            if [[ ${#ERRORS[@]} -le 5 ]]; then
                cecho "$RED" "  $ERR_MSG"
                if [[ -n "$RESULT" ]]; then
                    cecho "$DKRED" "    Response: ${RESULT:0:120}"
                fi
            fi
            ERRORS+=("$ERR_MSG")
            echo "$ERR_MSG" >> "$LOG_PATH"
        fi
    fi

    # Abort if clearly broken (20+ failures, 0 successes)
    if (( FAIL > 20 && SUCCESS == 0 )); then
        echo ""
        cecho "$RED" "ABORT: 20+ failures with 0 successes."
        cecho "$YELLOW" "Check that your neural-memory MCP server is running:"
        cecho "$YELLOW" "  mcporter list"
        cecho "$YELLOW" "  mcporter list neural-memory --schema"
        echo ""
        cecho "$YELLOW" "To resume from where this stopped, run:"
        cecho "$YELLOW" "  ./ingest_triples.sh --vault-path '$VAULT_PATH' --start-at $i"
        break
    fi

    sleep "$(echo "scale=3; $DELAY_MS/1000" | bc)"
done

# ── SUMMARY ───────────────────────────────────────────────────────────────────
NOW=$(date '+%s')
ELAPSED=$(( NOW - RUN_START ))
ELAPSED_STR="$(( ELAPSED / 60 ))m $(( ELAPSED % 60 ))s"

echo ""
cecho "$CYAN" "=== INGEST COMPLETE ==="
cecho "$GREEN" "  Successful: $SUCCESS"
[[ $FAIL -gt 0 ]] && cecho "$RED" "  Failed:     $FAIL" || cecho "$GRAY" "  Failed:     $FAIL"
cecho "$GRAY"  "  Skipped:    $SKIP"
cecho "$WHITE" "  Duration:   $ELAPSED_STR"
cecho "$GRAY"  "  Log:        $LOG_PATH"
echo ""

if [[ $SUCCESS -gt 0 && "$DRY_RUN" != "true" ]]; then
    cecho "$GREEN" "Your neural graph has been seeded with $SUCCESS facts from your history."
    cecho "$CYAN"  "Session 000 complete. Your AI already knows you."
fi

if [[ $FAIL -gt 0 ]]; then
    echo ""
    cecho "$YELLOW" "Some facts failed to ingest. Check $LOG_PATH for details."
    cecho "$YELLOW" "Retry failed items by checking the log for fact numbers"
    cecho "$YELLOW" "and rerunning with --start-at <number>."
fi

# Write summary to log
cat >> "$LOG_PATH" << EOF
=== Run Complete: $(date '+%Y-%m-%d %H:%M:%S') ===
Success: $SUCCESS | Failed: $FAIL | Skipped: $SKIP | Duration: $ELAPSED_STR
EOF
