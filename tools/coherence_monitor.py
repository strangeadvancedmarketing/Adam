"""
coherence_monitor.py — Adam Coherence Monitor (Layer 5)
Detects within-session coherence degradation via two signals:
  1. Scratchpad dropout — scratchpad tag absent from recent assistant turns
  2. Real token depth — actual input token count from OpenClaw session JSONL

HOW IT WORKS:
  Reads the active OpenClaw session JSONL file (one JSON object per line).
  Extracts assistant turns, checks scratchpad usage in the last N turns,
  reads real token counts from the usage field (no char estimation).
  When drift is confirmed, writes reanchor_pending.json for SENTINEL to consume.
  Logs every check event to coherence_log.json (session-scoped, reset at boot).

RUNS AS: Standalone script called by SENTINEL on a time interval.
  Suggested: every 5-10 minutes while gateway is active.

Exit codes:
  0 = coherent, no action taken
  1 = drift detected, reanchor_pending.json written
  2 = error (session unreadable, paths missing, etc.)
"""

import os
import re
import json
import logging
import sys
from datetime import datetime, date
from pathlib import Path

# ── PATHS ─────────────────────────────────────────────────────────────────────
VAULT_ROOT       = r"C:\AdamsVault"
WORKSPACE        = r"C:\AdamsVault\workspace"
AGENTS_MD        = r"C:\AdamsVault\workspace\AGENTS.md"
ACTIVE_CONTEXT   = r"C:\AdamsVault\workspace\active-context.md"
BASELINE_FILE    = r"C:\AdamsVault\workspace\coherence_baseline.json"
COHERENCE_LOG    = r"C:\AdamsVault\workspace\coherence_log.json"
REANCHOR_TRIGGER = r"C:\AdamsVault\workspace\reanchor_pending.json"
SESSIONS_DIR     = r"C:\Users\AJSup\.openclaw\agents\main\sessions"
CONTEXT_WINDOW   = 131072   # Kimi K2.5

# ── THRESHOLDS ────────────────────────────────────────────────────────────────
SCRATCHPAD_WINDOW       = 10    # assistant turns to look back
CONTEXT_DRIFT_THRESHOLD = 0.40  # 40% — drift risk begins
CONTEXT_WARN_THRESHOLD  = 0.65  # 65% — high risk, re-anchor regardless

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

def rlog(msg, level="INFO"):
    getattr(log, level.lower(), log.info)(msg)

# ── PART 1: BASELINE ──────────────────────────────────────────────────────────
def load_baseline():
    if not os.path.exists(BASELINE_FILE):
        return create_baseline()
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            b = json.load(f)
        # Invalidate if from a previous calendar day
        session_date = b.get("session_date", "")
        if session_date != str(date.today()):
            rlog("Baseline is from a previous session — resetting.", "WARNING")
            return create_baseline()
        return b
    except Exception as e:
        rlog(f"Baseline unreadable, resetting: {e}", "WARNING")
        return create_baseline()

def create_baseline():
    baseline = {
        "session_date":       str(date.today()),
        "session_start":      datetime.now().isoformat(),
        "scratchpad_expected": True,
        "context_window":     CONTEXT_WINDOW,
        "reinjections":       0,
        "last_check_turn":    0,
        "drift_events":       []
    }
    _save_baseline(baseline)
    rlog("Coherence baseline created for today.")
    return baseline

def _save_baseline(baseline):
    try:
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)
    except Exception as e:
        rlog(f"Failed to save baseline: {e}", "WARNING")


# ── PART 2: SESSION FILE FINDER ───────────────────────────────────────────────
def find_active_session():
    """
    Find the most recently modified .jsonl session file.
    Excludes: .lock files, .deleted. files, .reset. files, sessions.json index.
    Targets the live UUID session file only.
    """
    try:
        sessions_path = Path(SESSIONS_DIR)
        candidates = [
            f for f in sessions_path.iterdir()
            if f.suffix == ".jsonl"
            and ".deleted." not in f.name
            and ".reset." not in f.name
            and not f.name.endswith(".lock")
        ]
        if not candidates:
            rlog("No active session JSONL files found.", "WARNING")
            return None
        latest = max(candidates, key=lambda f: f.stat().st_mtime)
        rlog(f"Active session: {latest.name}")
        return str(latest)
    except Exception as e:
        rlog(f"Session file discovery failed: {e}", "ERROR")
        return None

# ── PART 3: JSONL SESSION READER ──────────────────────────────────────────────
SCRATCHPAD_RE = re.compile(r"<scratchpad>", re.IGNORECASE)

def read_session(session_path):
    """
    Parse OpenClaw JSONL session file (one JSON object per line).
    Returns:
      assistant_turns  — list of assistant message objects (with usage field)
      last_input_tokens — input token count from the most recent assistant turn
    """
    assistant_turns = []
    last_input_tokens = 0

    try:
        with open(session_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue  # Skip malformed lines silently

                if obj.get("type") != "message":
                    continue
                msg = obj.get("message", {})
                if msg.get("role") != "assistant":
                    continue

                assistant_turns.append(msg)
                usage = msg.get("usage", {})
                if usage.get("input", 0) > 0:
                    last_input_tokens = usage["input"]

    except Exception as e:
        rlog(f"Session read error: {e}", "ERROR")
        return [], 0

    return assistant_turns, last_input_tokens

def check_scratchpad(assistant_turns, window=SCRATCHPAD_WINDOW):
    """
    Check whether scratchpad tag fired in the last N assistant turns.
    Searches content array for thinking blocks and text blocks.
    Returns True if found (coherent), False if absent (potential drift).
    """
    recent = assistant_turns[-window:] if len(assistant_turns) >= window else assistant_turns
    for turn in recent:
        content = turn.get("content", [])
        if isinstance(content, list):
            for block in content:
                block_str = json.dumps(block)
                if SCRATCHPAD_RE.search(block_str):
                    return True
        elif isinstance(content, str):
            if SCRATCHPAD_RE.search(content):
                return True
    return False


# ── PART 4: DRIFT SCORING ─────────────────────────────────────────────────────
def score_drift(scratchpad_present, context_pct):
    """
    0.0 = fully coherent (scratchpad present, low context)
    0.2 = healthy pressure (scratchpad present, mid context)
    0.4 = pressure building (scratchpad present, high context)
    0.3 = early warning (scratchpad absent, low context)
    0.6 = drift likely (scratchpad absent, mid context)
    0.9 = drift confirmed (scratchpad absent, high context)

    NOTE: All scratchpad_present branches must be exhaustive — no fall-through.
    """
    if scratchpad_present:
        if context_pct < CONTEXT_DRIFT_THRESHOLD:
            return 0.0   # coherent, low pressure
        elif context_pct < CONTEXT_WARN_THRESHOLD:
            return 0.2   # coherent, moderate pressure — monitor only
        else:
            return 0.4   # coherent but deep context — soft warning
    else:
        if context_pct < CONTEXT_DRIFT_THRESHOLD:
            return 0.3   # scratchpad absent, low context — early warning
        elif context_pct < CONTEXT_WARN_THRESHOLD:
            return 0.6   # scratchpad absent, mid context — re-anchor
        else:
            return 0.9   # scratchpad absent, deep context — urgent re-anchor

def should_reanchor(drift_score, context_pct):
    # Only re-anchor on scratchpad dropout signals (score >= 0.6)
    # Context depth alone (scratchpad present) never triggers re-anchor
    return drift_score >= 0.6

# ── PART 5: COHERENCE LOG (SESSION-SCOPED) ────────────────────────────────────
def load_coherence_log():
    """Load log for today only — discard if stale."""
    if not os.path.exists(COHERENCE_LOG):
        return _fresh_log()
    try:
        with open(COHERENCE_LOG, "r", encoding="utf-8") as f:
            clog = json.load(f)
        if clog.get("session_date") != str(date.today()):
            return _fresh_log()
        return clog
    except Exception:
        return _fresh_log()

def _fresh_log():
    return {"session_date": str(date.today()), "events": []}

def append_coherence_event(turn, context_pct, scratchpad_present, drift_score, action):
    clog = load_coherence_log()
    clog["events"].append({
        "timestamp":        datetime.now().isoformat(),
        "turn":             turn,
        "context_pct":      round(context_pct, 4),
        "scratchpad_fired": scratchpad_present,
        "drift_score":      round(drift_score, 2),
        "action":           action
    })
    try:
        with open(COHERENCE_LOG, "w", encoding="utf-8") as f:
            json.dump(clog, f, indent=2)
    except Exception as e:
        rlog(f"Failed to write coherence log: {e}", "WARNING")


# ── PART 6: RE-ANCHOR CONTENT BUILDER ────────────────────────────────────────
def build_reanchor_content():
    """
    Pull identity-critical content from live Vault files.
    Target: ~200 tokens. Surgical re-anchor, not a full context reload.
    Falls back to a minimal hardcoded string if files are unreadable.

    IMPORTANT: The re-anchor content must NOT contain the literal string
    '<scratchpad>' — that string is the detection target in check_scratchpad().
    If the injected content contains it, the next coherence check finds a ghost
    hit and scores the session as coherent even when it isn't, OR scores it as
    drifting when the only hit is from the re-anchor block itself.
    All scratchpad tags are stripped from extracted content before injection.
    """
    # Sentinel string that must never appear in re-anchor output
    SCRATCHPAD_TAG = "<scratchpad>"
    SCRATCHPAD_PLACEHOLDER = "[SCRATCHPAD_LOOP_INSTRUCTION]"

    sections = []

    # Extract ReAct loop header from AGENTS.md
    try:
        with open(AGENTS_MD, "r", encoding="utf-8", errors="replace") as f:
            agents_text = f.read()
        match = re.search(
            r"(CRITICAL COGNITIVE FRAMEWORK.*?<scratchpad>)",
            agents_text, re.DOTALL
        )
        if match:
            # Strip the literal scratchpad tag — replace with neutral placeholder
            extracted = match.group(1)[:500].strip()
            extracted = extracted.replace(SCRATCHPAD_TAG, SCRATCHPAD_PLACEHOLDER)
            sections.append(extracted)
    except Exception as e:
        rlog(f"AGENTS.md read failed for re-anchor: {e}", "WARNING")

    # Extract Priority 1 block from active-context.md
    try:
        with open(ACTIVE_CONTEXT, "r", encoding="utf-8", errors="replace") as f:
            ctx_text = f.read()
        match = re.search(
            r"(## 🔥 Priority 1:.*?)(?=## 🔥 Priority 2:|^---|$)",
            ctx_text, re.DOTALL | re.MULTILINE
        )
        if match:
            sections.append(match.group(1).strip()[:350])
    except Exception as e:
        rlog(f"active-context.md read failed for re-anchor: {e}", "WARNING")

    if not sections:
        return (
            "COHERENCE RE-ANCHOR: Scratchpad dropout detected. "
            "Re-engage your ReAct cognitive loop before responding. "
            "Check active-context.md for current priorities."
        )

    return (
        "⚠️ COHERENCE RE-ANCHOR — Scratchpad dropout detected.\n"
        "Re-engage your ReAct cognitive loop now.\n\n"
        + "\n\n---\n\n".join(sections)
    )

def write_reanchor_trigger(content, turn, drift_score):
    """
    Write reanchor_pending.json.
    SENTINEL polls for this file. When found with consumed=false,
    SENTINEL injects content into the next message context, then sets consumed=true.

    DEDUPLICATION: If a pending re-anchor already exists with consumed=false,
    this function does NOT overwrite it. The existing trigger is still waiting
    for SENTINEL to consume it — writing a second one would cause a race where
    SENTINEL marks the first consumed, the monitor immediately writes a new one,
    and BOOT_CONTEXT.md accumulates a re-anchor block every 5 minutes.

    Returns True if written, False if skipped (already pending).
    """
    # Guard: don't overwrite an unconsumed pending re-anchor
    if os.path.exists(REANCHOR_TRIGGER):
        try:
            with open(REANCHOR_TRIGGER, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not existing.get("consumed", True):
                rlog(f"Re-anchor already pending (turn {existing.get('turn')}, "
                     f"score {existing.get('drift_score')}) — skipping duplicate write.")
                return False
        except Exception:
            pass  # Unreadable file — overwrite it

    payload = {
        "created_at":  datetime.now().isoformat(),
        "turn":        turn,
        "drift_score": round(drift_score, 2),
        "content":     content,
        "consumed":    False
    }
    try:
        with open(REANCHOR_TRIGGER, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        rlog(f"reanchor_pending.json written. Turn: {turn}, Score: {drift_score}")
        return True
    except Exception as e:
        rlog(f"Failed to write re-anchor trigger: {e}", "ERROR")
        return False


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    rlog("=" * 60)
    rlog("Adam Coherence Monitor starting")
    rlog("=" * 60)

    baseline = load_baseline()

    session_path = find_active_session()
    if not session_path:
        rlog("No active session — exiting clean.")
        sys.exit(0)

    assistant_turns, last_input_tokens = read_session(session_path)
    total_turns = len(assistant_turns)
    rlog(f"Assistant turns found: {total_turns}")
    rlog(f"Last input token count: {last_input_tokens}")

    if total_turns == 0:
        rlog("No assistant turns yet — session too new to evaluate.")
        sys.exit(0)

    # Real context depth from token usage (not char estimation)
    context_pct = min(last_input_tokens / CONTEXT_WINDOW, 1.0)
    rlog(f"Context depth: {last_input_tokens}/{CONTEXT_WINDOW} = {context_pct*100:.1f}%")

    scratchpad_present = check_scratchpad(assistant_turns)
    rlog(f"Scratchpad in last {SCRATCHPAD_WINDOW} turns: {scratchpad_present}")

    drift_score = score_drift(scratchpad_present, context_pct)
    rlog(f"Drift score: {drift_score}")

    if not should_reanchor(drift_score, context_pct):
        rlog("Session coherent — no action needed.")
        append_coherence_event(
            total_turns, context_pct, scratchpad_present, drift_score, "coherent"
        )
        baseline["last_check_turn"] = total_turns
        _save_baseline(baseline)
        sys.exit(0)

    # Drift confirmed
    rlog("DRIFT DETECTED — writing re-anchor trigger.", "WARNING")
    reanchor_content = build_reanchor_content()
    written = write_reanchor_trigger(reanchor_content, total_turns, drift_score)

    if written:
        action = "reanchor_triggered"
    else:
        action = "reanchor_skipped_pending"
        rlog("Re-anchor already pending — SENTINEL has not consumed previous trigger yet.")

    append_coherence_event(
        total_turns, context_pct, scratchpad_present, drift_score, action
    )

    baseline["last_check_turn"] = total_turns
    if written:
        baseline["reinjections"] = baseline.get("reinjections", 0) + 1
        baseline["drift_events"] = baseline.get("drift_events", []) + [{
            "turn":        total_turns,
            "context_pct": round(context_pct, 4),
            "drift_score": drift_score,
            "timestamp":   datetime.now().isoformat()
        }]
    _save_baseline(baseline)

    rlog(f"Re-anchor complete. Session reinjections: {baseline['reinjections']}")
    sys.exit(1)


if __name__ == "__main__":
    main()
