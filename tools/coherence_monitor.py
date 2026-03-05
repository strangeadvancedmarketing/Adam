"""
coherence_monitor.py — Adam Coherence Monitor (Layer 5)
Detects within-session coherence degradation by tracking scratchpad usage
and context depth. Injects a re-anchor when drift is detected.

HOW IT WORKS:
  - Reads the OpenClaw session log to detect scratchpad usage per turn block
  - Tracks context depth via a lightweight token estimate
  - When scratchpad dropout + depth threshold are both met: drift confirmed
  - Writes coherence_log.json for the current session
  - Re-anchor injection: writes a re-anchor trigger file that SENTINEL watches

RUNS AS: Standalone script, called by SENTINEL on a turn interval
  Example (in SENTINEL): every 10 Telegram messages, call this script.

Exit codes: 0 = coherent, 1 = drift detected (re-anchor triggered), 2 = error
"""

import os
import re
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# ── PATHS ────────────────────────────────────────────────────────────────────
VAULT_ROOT          = r"C:\AdamsVault"
WORKSPACE           = r"C:\AdamsVault\workspace"
AGENTS_MD           = r"C:\AdamsVault\workspace\AGENTS.md"
ACTIVE_CONTEXT      = r"C:\AdamsVault\workspace\active-context.md"
SOUL_MD             = r"C:\AdamsVault\workspace\SOUL.md"
BASELINE_FILE       = r"C:\AdamsVault\workspace\coherence_baseline.json"
COHERENCE_LOG       = r"C:\AdamsVault\workspace\coherence_log.json"
REANCHOR_TRIGGER    = r"C:\AdamsVault\workspace\reanchor_pending.json"
OPENCLAW_SESSIONS   = r"C:\Users\AJSup\.openclaw\agents"

# ── THRESHOLDS ───────────────────────────────────────────────────────────────
# Drift is confirmed when BOTH signals are true:
#   1. No scratchpad usage in the last SCRATCHPAD_WINDOW turns
#   2. Estimated context depth exceeds CONTEXT_DRIFT_THRESHOLD (as % of window)
SCRATCHPAD_WINDOW       = 10    # turns to look back for scratchpad absence
CONTEXT_DRIFT_THRESHOLD = 0.40  # 40% context consumed — drift risk zone begins
CONTEXT_WARN_THRESHOLD  = 0.65  # 65% — high risk, re-anchor even without dropout

# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

run_start = datetime.now()

def rlog(msg, level="INFO"):
    getattr(log, level.lower(), log.info)(msg)

# ── PART 1: BASELINE ─────────────────────────────────────────────────────────
def load_baseline():
    """Load or create the session coherence baseline."""
    if not os.path.exists(BASELINE_FILE):
        return create_baseline()
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        rlog(f"Baseline file unreadable, recreating: {e}", "WARNING")
        return create_baseline()

def create_baseline():
    """
    Write coherence_baseline.json at session start.
    Called by SENTINEL during boot, before gateway launch.
    Establishes what 'coherent Adam' looks like for this session.
    """
    baseline = {
        "session_start":        datetime.now().isoformat(),
        "scratchpad_expected":  True,
        "context_window_tokens": 131072,   # Kimi K2.5 context window
        "estimated_tokens_used": 0,
        "reinjections":         0,
        "last_check_turn":      0,
        "drift_events":         []
    }
    try:
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)
        rlog("Coherence baseline created.")
    except Exception as e:
        rlog(f"Failed to write baseline: {e}", "ERROR")
    return baseline

def save_baseline(baseline):
    try:
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)
    except Exception as e:
        rlog(f"Failed to save baseline: {e}", "WARNING")


# ── PART 2: SESSION LOG READER ────────────────────────────────────────────────
def find_active_session():
    """
    Locate the most recently modified session file in OpenClaw's agents directory.
    OpenClaw writes live session JSON as messages accumulate.
    """
    try:
        session_dir = Path(OPENCLAW_SESSIONS)
        sessions = list(session_dir.glob("sessions*.json"))
        if not sessions:
            # Try flat sessions.json
            flat = session_dir / "sessions.json"
            if flat.exists():
                return str(flat)
            rlog("No session files found in OpenClaw agents directory.", "WARNING")
            return None
        # Most recently modified
        latest = max(sessions, key=os.path.getmtime)
        return str(latest)
    except Exception as e:
        rlog(f"Could not locate session file: {e}", "WARNING")
        return None

def count_turns_and_scratchpad(session_path, window=SCRATCHPAD_WINDOW):
    """
    Read the OpenClaw session JSON and return:
      - total_turns: number of assistant turns in session
      - scratchpad_in_window: True if ANY scratchpad tag found in last N turns
      - estimated_tokens: rough token count (chars / 4)
    """
    try:
        with open(session_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        # OpenClaw session format: list of message objects with role/content
        messages = data if isinstance(data, list) else data.get("messages", [])

        assistant_turns = [
            m for m in messages
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]

        total_turns = len(assistant_turns)
        recent_turns = assistant_turns[-window:] if total_turns >= window else assistant_turns

        # Scratchpad detection — check for opening tag
        scratchpad_pattern = re.compile(r"<scratchpad>", re.IGNORECASE)
        scratchpad_in_window = any(
            scratchpad_pattern.search(str(t.get("content", "")))
            for t in recent_turns
        )

        # Rough token estimate: total chars in all messages / 4
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        estimated_tokens = total_chars // 4

        return total_turns, scratchpad_in_window, estimated_tokens

    except Exception as e:
        rlog(f"Session read failed: {e}", "WARNING")
        return 0, True, 0   # Default: assume coherent if unreadable


# ── PART 3: DRIFT SCORING ─────────────────────────────────────────────────────
def score_drift(scratchpad_present, context_pct):
    """
    Compute a drift score 0.0–1.0.
      0.0 = fully coherent
      1.0 = maximum detected drift

    Scoring logic:
      - Scratchpad present + low context   = 0.0  (coherent)
      - Scratchpad absent + low context    = 0.3  (early warning)
      - Scratchpad present + high context  = 0.4  (pressure building)
      - Scratchpad absent + mid context    = 0.6  (drift likely)
      - Scratchpad absent + high context   = 0.9  (drift confirmed)
    """
    if scratchpad_present and context_pct < CONTEXT_DRIFT_THRESHOLD:
        return 0.0
    if scratchpad_present and context_pct >= CONTEXT_WARN_THRESHOLD:
        return 0.4
    if not scratchpad_present and context_pct < CONTEXT_DRIFT_THRESHOLD:
        return 0.3
    if not scratchpad_present and context_pct < CONTEXT_WARN_THRESHOLD:
        return 0.6
    if not scratchpad_present and context_pct >= CONTEXT_WARN_THRESHOLD:
        return 0.9
    return 0.0

def should_reanchor(drift_score, context_pct):
    """
    Trigger re-anchor when:
      - Drift score >= 0.6 (scratchpad absent + meaningful context depth)
      - OR context alone is at critical threshold (>= 65%) regardless of scratchpad
    """
    return drift_score >= 0.6 or context_pct >= CONTEXT_WARN_THRESHOLD

# ── PART 4: COHERENCE LOG ────────────────────────────────────────────────────
def load_coherence_log():
    if not os.path.exists(COHERENCE_LOG):
        return {"session_start": datetime.now().isoformat(), "events": []}
    try:
        with open(COHERENCE_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"session_start": datetime.now().isoformat(), "events": []}

def append_coherence_event(turn, context_pct, scratchpad_fired, drift_score, action):
    clog = load_coherence_log()
    clog["events"].append({
        "timestamp":        datetime.now().isoformat(),
        "turn":             turn,
        "context_pct":      round(context_pct, 3),
        "scratchpad_fired": scratchpad_fired,
        "drift_score":      round(drift_score, 2),
        "action":           action
    })
    try:
        with open(COHERENCE_LOG, "w", encoding="utf-8") as f:
            json.dump(clog, f, indent=2)
    except Exception as e:
        rlog(f"Failed to write coherence log: {e}", "WARNING")


# ── PART 5: RE-ANCHOR CONTENT BUILDER ────────────────────────────────────────
def build_reanchor_content():
    """
    Build the re-anchor payload from live Vault files.
    Pulls the ReAct loop definition from AGENTS.md and current
    top priorities from active-context.md.
    Target: ~200 tokens. Surgical, not a full context reload.
    """
    sections = []

    # Pull ReAct loop header from AGENTS.md
    try:
        with open(AGENTS_MD, "r", encoding="utf-8", errors="replace") as f:
            agents_content = f.read()
        # Extract just the COGNITION ENGINE section header + first instruction
        react_match = re.search(
            r"(## .{0,20}COGNITION ENGINE.*?<scratchpad>)",
            agents_content,
            re.DOTALL
        )
        if react_match:
            sections.append(react_match.group(1)[:600])  # cap at 600 chars
    except Exception as e:
        rlog(f"Could not read AGENTS.md for re-anchor: {e}", "WARNING")

    # Pull Priority 1 from active-context.md
    try:
        with open(ACTIVE_CONTEXT, "r", encoding="utf-8", errors="replace") as f:
            ctx_content = f.read()
        prio_match = re.search(r"(## 🔥 Priority 1:.*?)(?=## 🔥 Priority 2:|---|\Z)", ctx_content, re.DOTALL)
        if prio_match:
            sections.append(prio_match.group(1).strip()[:400])  # cap at 400 chars
    except Exception as e:
        rlog(f"Could not read active-context.md for re-anchor: {e}", "WARNING")

    if not sections:
        # Fallback: bare minimum re-anchor
        return "COHERENCE RE-ANCHOR: Use your scratchpad ReAct loop before responding. Check active-context.md priorities."

    reanchor = (
        "⚠️ COHERENCE RE-ANCHOR — Context depth detected in drift zone.\n"
        "Your scratchpad ReAct loop has not fired recently. Re-engage now.\n\n"
        + "\n\n".join(sections)
    )
    return reanchor

def write_reanchor_trigger(content, turn, drift_score):
    """
    Write reanchor_pending.json — SENTINEL watches this file.
    When present, SENTINEL injects the re-anchor into the next
    message context before it reaches the model.
    """
    payload = {
        "created_at":   datetime.now().isoformat(),
        "turn":         turn,
        "drift_score":  drift_score,
        "content":      content,
        "consumed":     False
    }
    try:
        with open(REANCHOR_TRIGGER, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        rlog(f"Re-anchor trigger written. Turn: {turn}, Drift score: {drift_score}")
    except Exception as e:
        rlog(f"Failed to write re-anchor trigger: {e}", "ERROR")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    rlog("=" * 60)
    rlog("Adam Coherence Monitor — coherence_monitor.py starting")
    rlog("=" * 60)

    # Part 1: Load baseline
    baseline = load_baseline()

    # Part 2: Find and read active session
    session_path = find_active_session()
    if not session_path:
        rlog("No active session found — nothing to monitor.")
        sys.exit(0)

    rlog(f"Session file: {session_path}")
    total_turns, scratchpad_present, estimated_tokens = count_turns_and_scratchpad(session_path)

    # Part 3: Compute context depth
    context_window = baseline.get("context_window_tokens", 131072)
    context_pct = min(estimated_tokens / context_window, 1.0)

    rlog(f"Turn count: {total_turns}")
    rlog(f"Scratchpad in last {SCRATCHPAD_WINDOW} turns: {scratchpad_present}")
    rlog(f"Estimated tokens: {estimated_tokens} / {context_window} ({context_pct*100:.1f}%)")

    # Part 4: Score drift
    drift_score = score_drift(scratchpad_present, context_pct)
    rlog(f"Drift score: {drift_score}")

    # Part 5: Decide action
    if not should_reanchor(drift_score, context_pct):
        action = "coherent"
        rlog("Session coherent — no action needed.")
        append_coherence_event(total_turns, context_pct, scratchpad_present, drift_score, action)

        # Update baseline
        baseline["last_check_turn"] = total_turns
        baseline["estimated_tokens_used"] = estimated_tokens
        save_baseline(baseline)

        sys.exit(0)

    # Drift confirmed — build and write re-anchor
    rlog("DRIFT DETECTED — building re-anchor.", "WARNING")
    reanchor_content = build_reanchor_content()
    write_reanchor_trigger(reanchor_content, total_turns, drift_score)

    action = "reanchor_triggered"
    append_coherence_event(total_turns, context_pct, scratchpad_present, drift_score, action)

    # Update baseline counters
    baseline["last_check_turn"] = total_turns
    baseline["estimated_tokens_used"] = estimated_tokens
    baseline["reinjections"] = baseline.get("reinjections", 0) + 1
    baseline["drift_events"] = baseline.get("drift_events", []) + [{
        "turn": total_turns,
        "context_pct": round(context_pct, 3),
        "drift_score": drift_score,
        "timestamp": datetime.now().isoformat()
    }]
    save_baseline(baseline)

    rlog(f"Re-anchor triggered. Total re-injections this session: {baseline['reinjections']}")
    sys.exit(1)   # Exit 1 = drift detected, SENTINEL can act on this


if __name__ == "__main__":
    main()
