"""
coherence_monitor.py — Adam Coherence Monitor (Layer 5)
Detects within-session coherence degradation via token depth only.

VERSION: 2.0.0 — Model-agnostic rewrite (2026-03-20)
CHANGE: Removed scratchpad detection. Different models (Kimi, DeepSeek, Claude)
        follow XML tag instructions differently. Scratchpad detection only worked
        reliably with Kimi K2.5. Now uses pure token depth as the drift signal.

HOW IT WORKS:
  Reads the active OpenClaw session JSONL file (one JSON object per line).
  Reads real token counts from the usage field (no char estimation).
  When context exceeds threshold, writes reanchor_pending.json for SENTINEL.
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
# v2.0: Scratchpad detection removed — model-agnostic token depth only
CONTEXT_DRIFT_THRESHOLD = 0.50  # 50% — start monitoring closely
CONTEXT_WARN_THRESHOLD  = 0.70  # 70% — trigger re-anchor
CONTEXT_CRITICAL        = 0.85  # 85% — urgent, compaction imminent

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
def read_session(session_path):
    """
    Parse OpenClaw JSONL session file (one JSON object per line).
    Returns:
      turn_count      — total number of assistant turns
      last_input_tokens — input token count from the most recent assistant turn
      model_id        — model string from the most recent assistant turn
    """
    turn_count = 0
    last_input_tokens = 0
    model_id = "unknown"

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

                turn_count += 1
                usage = msg.get("usage", {})
                if usage.get("input", 0) > 0:
                    last_input_tokens = usage["input"]
                if msg.get("model"):
                    model_id = msg["model"]

    except Exception as e:
        rlog(f"Session read error: {e}", "ERROR")
        return 0, 0, "unknown"

    return turn_count, last_input_tokens, model_id


# ── PART 4: DRIFT SCORING (TOKEN DEPTH ONLY) ──────────────────────────────────
def score_drift(context_pct):
    """
    v2.0: Model-agnostic scoring based purely on token depth.
    
    0.0 = healthy (< 50% context)
    0.3 = moderate pressure (50-70% context)  
    0.7 = high pressure, re-anchor (70-85% context)
    0.9 = critical, compaction imminent (> 85% context)
    """
    if context_pct < CONTEXT_DRIFT_THRESHOLD:
        return 0.0   # healthy
    elif context_pct < CONTEXT_WARN_THRESHOLD:
        return 0.3   # moderate pressure — monitor only
    elif context_pct < CONTEXT_CRITICAL:
        return 0.7   # high pressure — re-anchor
    else:
        return 0.9   # critical — urgent re-anchor

def should_reanchor(drift_score):
    """Re-anchor when score >= 0.7 (context at 70%+)"""
    return drift_score >= 0.7

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

def append_coherence_event(turn, context_pct, drift_score, action, model_id="unknown"):
    clog = load_coherence_log()
    clog["events"].append({
        "timestamp":        datetime.now().isoformat(),
        "turn":             turn,
        "context_pct":      round(context_pct, 4),
        "drift_score":      round(drift_score, 2),
        "action":           action,
        "model":            model_id
    })
    try:
        with open(COHERENCE_LOG, "w", encoding="utf-8") as f:
            json.dump(clog, f, indent=2)
    except Exception as e:
        rlog(f"Failed to write coherence log: {e}", "WARNING")


# ── PART 6: RE-ANCHOR CONTENT BUILDER ────────────────────────────────────────
def build_reanchor_content():
    """
    v2.0: Simplified re-anchor — just remind to check active-context.
    No scratchpad instruction injection needed since we're not detecting it.
    """
    sections = []

    # Extract Priority 1 block from active-context.md
    try:
        with open(ACTIVE_CONTEXT, "r", encoding="utf-8", errors="replace") as f:
            ctx_text = f.read()
        match = re.search(
            r"(## 🔥 Priority 1:.*?)(?=## 🔥 Priority 2:|^---|$)",
            ctx_text, re.DOTALL | re.MULTILINE
        )
        if match:
            sections.append(match.group(1).strip()[:500])
    except Exception as e:
        rlog(f"active-context.md read failed for re-anchor: {e}", "WARNING")

    if not sections:
        return (
            "⚠️ CONTEXT PRESSURE: Session approaching token limit. "
            "Review active-context.md for current priorities. "
            "Consider wrapping up current task or requesting compaction."
        )

    return (
        "⚠️ CONTEXT PRESSURE — Session at high token depth.\n"
        "Current priorities:\n\n"
        + "\n\n".join(sections)
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
    rlog("Adam Coherence Monitor v2.0 (model-agnostic)")
    rlog("=" * 60)

    baseline = load_baseline()

    session_path = find_active_session()
    if not session_path:
        rlog("No active session — exiting clean.")
        sys.exit(0)

    turn_count, last_input_tokens, model_id = read_session(session_path)
    rlog(f"Model: {model_id}")
    rlog(f"Assistant turns: {turn_count}")
    rlog(f"Last input tokens: {last_input_tokens}")

    if turn_count == 0:
        rlog("No assistant turns yet — session too new to evaluate.")
        sys.exit(0)

    # Real context depth from token usage (not char estimation)
    context_pct = min(last_input_tokens / CONTEXT_WINDOW, 1.0)
    rlog(f"Context depth: {last_input_tokens}/{CONTEXT_WINDOW} = {context_pct*100:.1f}%")

    drift_score = score_drift(context_pct)
    rlog(f"Drift score: {drift_score}")

    if not should_reanchor(drift_score):
        rlog("Session healthy — no action needed.")
        append_coherence_event(turn_count, context_pct, drift_score, "healthy", model_id)
        baseline["last_check_turn"] = turn_count
        _save_baseline(baseline)
        sys.exit(0)

    # Context pressure detected
    rlog("CONTEXT PRESSURE — writing re-anchor trigger.", "WARNING")
    reanchor_content = build_reanchor_content()
    written = write_reanchor_trigger(reanchor_content, turn_count, drift_score)

    if written:
        action = "reanchor_triggered"
    else:
        action = "reanchor_skipped_pending"
        rlog("Re-anchor already pending — SENTINEL has not consumed previous trigger yet.")

    append_coherence_event(turn_count, context_pct, drift_score, action, model_id)

    baseline["last_check_turn"] = turn_count
    if written:
        baseline["reinjections"] = baseline.get("reinjections", 0) + 1
        baseline["drift_events"] = baseline.get("drift_events", []) + [{
            "turn":        turn_count,
            "context_pct": round(context_pct, 4),
            "drift_score": drift_score,
            "timestamp":   datetime.now().isoformat()
        }]
    _save_baseline(baseline)

    rlog(f"Re-anchor complete. Session reinjections: {baseline['reinjections']}")
    sys.exit(1)


if __name__ == "__main__":
    main()
