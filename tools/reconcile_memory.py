#!/usr/bin/env python3
"""
Adam Framework — Sleep Cycle (reconcile_memory.py)

Nightly memory consolidation. Runs automatically via SENTINEL before each
gateway launch (if more than 6 hours since last run).

What it does:
  1. Reads unprocessed daily session logs from your Vault
  2. Calls an LLM to merge them into your CORE_MEMORY.md
  3. Incrementally ingests new facts into the neural graph (diff-only, no nuke)
  4. Defers vector reindex to SENTINEL (runs after gateway is confirmed healthy)

Vector reindex is intentionally NOT done here — the gateway must be live first.
SENTINEL handles that handoff. See engine/SENTINEL.template.ps1.

Usage:
  python reconcile_memory.py --vault-path C:/YourVault --api-key YOUR_GEMINI_KEY
  python reconcile_memory.py --vault-path C:/YourVault --api-key YOUR_GEMINI_KEY --dry-run
  python reconcile_memory.py --vault-path C:/YourVault --config path/to/openclaw.json

The --config flag reads the Gemini key from your openclaw.json automatically.

Exit codes:
  0 = success (or nothing to process)
  1 = partial (core memory updated but neural ingest skipped)
  2 = failed  (core memory NOT updated — original preserved)
"""

import os
import re
import sys
import json
import time
import shutil
import difflib
import logging
import argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Run: pip install requests")
    sys.exit(2)


# ── CONSTANTS ─────────────────────────────────────────────────────────────────
MAX_LOGS_PER_RUN = 14   # Rolling window — prevents LLM context overflow
MAX_BACKUPS      = 7    # How many CORE_MEMORY backups to keep

GEMINI_ENDPOINT  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# System prompt for the reconciliation LLM call.
# Model-agnostic — works with Gemini, OpenAI, Anthropic, or any instruction-following model.
# The key constraint is temperature: 0.1 — this must be deterministic, not creative.
SYSTEM_PROMPT = """You are a strict memory reconciliation system for an AI assistant.
Your job is to merge daily session logs into the master core memory file.

Rules:
- Preserve ALL existing sections and headers exactly as they appear
- Mark completed tasks as done, or remove them if fully resolved
- Add new permanent facts, contacts, decisions, and project updates from the daily logs
- Resolve contradictions by preferring the most recent information
- Do NOT add commentary, preamble, or notes about what you changed
- Return ONLY the complete rewritten Markdown file — nothing else, no code fences
- The output must start with the first # header of the file"""


# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

run_start    = datetime.now()
run_log_lines = []

def rlog(msg, level="INFO"):
    getattr(log, level.lower(), log.info)(msg)
    run_log_lines.append(f"  {msg}")


# ── CONFIG ────────────────────────────────────────────────────────────────────

def resolve_paths(vault_path: str) -> dict:
    """Derive all file paths from the vault root."""
    v = Path(vault_path)
    return {
        "vault_root":    v,
        "core_memory":   v / "CORE_MEMORY.md",
        "logs_dir":      v / "workspace" / "memory",
        "backup_dir":    v / "workspace" / "memory" / "_reconcile_backups",
        "state_file":    v / "workspace" / "memory" / "_reconcile_state.json",
        "reconcile_log": v / "workspace" / "memory" / "_reconcile_log.md",
    }


def get_api_key_from_config(config_path: str) -> str:
    """
    Try to read a Gemini API key from an openclaw.json or mcporter.json config.
    Looks in common locations within the config structure.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # openclaw.json style: env block at top level
        if "env" in cfg and "GEMINI_API_KEY" in cfg["env"]:
            return cfg["env"]["GEMINI_API_KEY"]

        # mcporter.json style: nested under mcpServers.gemini.env
        servers = cfg.get("mcpServers", cfg.get("servers", {}))
        gemini  = servers.get("gemini", {})
        key     = gemini.get("env", {}).get("GEMINI_API_KEY", "")
        if key:
            return key

    except Exception as e:
        rlog(f"Could not read API key from config: {e}", "WARNING")

    return ""


# ── STATE ─────────────────────────────────────────────────────────────────────

def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {"last_reconcile_run": "2000-01-01", "processed_logs": []}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        rlog(f"State file corrupt, starting fresh: {e}", "WARNING")
        return {"last_reconcile_run": "2000-01-01", "processed_logs": []}


def save_state(state_file: Path, state: dict):
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        rlog(f"Failed to save state: {e}", "WARNING")


def get_unprocessed_logs(logs_dir: Path, state: dict) -> list:
    """Find daily log files not yet processed. Pattern: YYYY-MM-DD*.md"""
    if not logs_dir.exists():
        return []
    processed   = set(state.get("processed_logs", []))
    log_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}.*\.md$")
    return sorted([
        f for f in os.listdir(logs_dir)
        if log_pattern.match(f)
        and not f.startswith("_")
        and f not in processed
    ])


# ── BACKUP ────────────────────────────────────────────────────────────────────

def backup_core_memory(core_memory: Path, backup_dir: Path) -> Path | None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp   = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = backup_dir / f"CORE_MEMORY_{timestamp}.md"
    try:
        shutil.copy2(core_memory, backup_path)
        rlog(f"Backup created: {backup_path}")
    except Exception as e:
        rlog(f"BACKUP FAILED: {e}", "ERROR")
        return None

    # Prune oldest backups beyond the keep limit
    try:
        backups = sorted(backup_dir.glob("CORE_MEMORY_*.md"), key=os.path.getmtime)
        for old in backups[:-MAX_BACKUPS]:
            os.remove(old)
    except Exception as e:
        rlog(f"Backup pruning failed (non-fatal): {e}", "WARNING")

    return backup_path


# ── LLM CALL ─────────────────────────────────────────────────────────────────

def call_gemini(api_key: str, core_content: str, logs_content: str,
                date_range: str, n_logs: int) -> str | None:
    """
    Call Gemini API to reconcile daily logs into core memory.
    Retries on rate limits with backoff. Returns reconciled markdown or None.
    """
    user_message = (
        f"CURRENT CORE MEMORY:\n---\n{core_content}\n---\n\n"
        f"UNPROCESSED DAILY LOGS ({n_logs} logs, {date_range}):\n---\n{logs_content}\n---\n\n"
        "Return the fully reconciled CORE_MEMORY.md."
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents":           [{"parts": [{"text": user_message}]}],
        "generationConfig":   {"temperature": 0.1, "maxOutputTokens": 8000}
    }
    url    = f"{GEMINI_ENDPOINT}?key={api_key}"
    delays = [5, 15, 45]

    for attempt, delay in enumerate(delays):
        try:
            rlog(f"Calling Gemini API (attempt {attempt + 1}/{len(delays)})...")
            resp = requests.post(url, json=payload, timeout=90)

            if resp.status_code == 429:
                if attempt < len(delays) - 1:
                    rlog(f"Rate limited. Waiting {delay}s...", "WARNING")
                    time.sleep(delay)
                    continue
                rlog("Rate limited on all attempts.", "ERROR")
                return None

            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()

        except requests.Timeout:
            rlog(f"Timeout on attempt {attempt + 1}", "WARNING")
            if attempt == len(delays) - 1:
                rlog("All attempts timed out.", "ERROR")
                return None
        except Exception as e:
            rlog(f"API error: {e}", "ERROR")
            return None

    return None


def validate_response(response: str, original_content: str) -> bool:
    """
    Sanity-check the LLM response before overwriting core memory.
    Checks: non-empty, starts with header, reasonable length ratio.
    Does NOT check for specific section numbers — those vary by user's file structure.
    """
    if not response:
        rlog("Validation failed: empty response", "ERROR")
        return False

    if not response.lstrip().startswith("#"):
        rlog("Validation failed: response does not start with a Markdown header", "ERROR")
        return False

    orig_len = len(original_content)
    resp_len = len(response)

    if orig_len > 0:
        ratio = resp_len / orig_len
        if ratio < 0.4 or ratio > 2.5:
            rlog(f"Validation failed: length ratio {ratio:.2f} outside safe bounds [0.4, 2.5]", "ERROR")
            rlog(f"  Original: {orig_len} chars, Response: {resp_len} chars", "ERROR")
            return False

    rlog("Response validation passed.")
    return True


# ── NEURAL INGEST ─────────────────────────────────────────────────────────────

def split_facts(text: str) -> list:
    """
    Split text into fact sentences.
    Uses smart split that respects file extensions, decimals, URLs, and paths.
    """
    sentences = re.split(r'(?<![.\d/\\A-Za-z])\.\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def ingest_neural(old_content: str, new_content: str) -> int:
    """
    Incrementally ingest only new/changed facts into the neural graph.
    Uses diff to find added lines — does NOT nuke and rebuild the whole graph.
    Falls back gracefully if neural_memory is not installed.
    """
    try:
        from neural_memory import NeuralMemory
    except ImportError:
        rlog("neural_memory package not installed — neural ingest skipped.", "WARNING")
        rlog("Install with: pip install neural-memory", "WARNING")
        return 0

    try:
        diff = difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            lineterm=""
        )
        added_lines = [
            line[1:] for line in diff
            if line.startswith("+") and not line.startswith("+++")
        ]
        added_text = " ".join(added_lines)
        facts      = split_facts(added_text)

        if not facts:
            rlog("Neural ingest: no new facts detected in diff.")
            return 0

        nm    = NeuralMemory(brain_id="default")
        count = 0
        for fact in facts:
            try:
                nm.remember(fact)
                count += 1
            except Exception as e:
                rlog(f"Neural remember skipped: {e}", "WARNING")

        rlog(f"Neural ingest: {count} new facts added to graph.")
        return count

    except Exception as e:
        rlog(f"Neural ingest error (non-fatal): {e}", "WARNING")
        return 0


# ── COMPLETION LOG ────────────────────────────────────────────────────────────

def snapshot_neural_metrics(vault_path: Path, neurons: int, synapses: int):
    """
    Append a timestamped neural metrics snapshot to neural_metrics.json.
    Creates the file if it doesn't exist. Called after every successful reconcile run.
    This is the data source for the README 'last measured' badge and growth log.
    """
    metrics_file = vault_path / "workspace" / "neural_metrics.json"
    try:
        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        else:
            metrics = {"snapshots": []}

        metrics["snapshots"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "neurons":   neurons,
            "synapses":  synapses
        })

        # Keep last 365 snapshots (1 year of daily runs)
        metrics["snapshots"] = metrics["snapshots"][-365:]
        metrics["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metrics["latest"] = {"neurons": neurons, "synapses": synapses}

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        rlog(f"Neural metrics snapshot written: {neurons} neurons / {synapses} synapses")
        return True
    except Exception as e:
        rlog(f"Neural metrics snapshot failed (non-fatal): {e}", "WARNING")
        return False


def get_neural_stats() -> tuple[int, int]:
    """
    Query the neural graph for current neuron and synapse counts.
    Returns (neurons, synapses) or (0, 0) if unavailable.
    """
    try:
        from neural_memory import NeuralMemory
        nm = NeuralMemory(brain_id="default")
        stats = nm.stats()
        neurons  = stats.get("neurons",  stats.get("node_count",  0))
        synapses = stats.get("synapses", stats.get("edge_count",  0))
        return int(neurons), int(synapses)
    except Exception as e:
        rlog(f"Could not query neural stats (non-fatal): {e}", "WARNING")
        return 0, 0


def write_reconcile_log(reconcile_log: Path, processed: list, total: int,
                        deferred: int, old_lines: int, new_lines: int,
                        neural_count: int, neural_skipped: str, status: str,
                        neurons: int = 0, synapses: int = 0):
    elapsed    = (datetime.now() - run_start).total_seconds()
    timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    neural_str = f"SKIPPED ({neural_skipped})" if neural_skipped else f"{neural_count} new facts"
    neural_size = f"{neurons:,} neurons / {synapses:,} synapses" if neurons else "unavailable"
    entry = (
        f"\n## Reconcile Run — {timestamp}\n"
        f"- Logs processed: {processed} ({len(processed)} of {total} — {deferred} deferred)\n"
        f"- Core memory: {old_lines} → {new_lines} lines\n"
        f"- Vector reindex: DEFERRED TO SENTINEL (fires after gateway health check)\n"
        f"- Neural ingest: {neural_str}\n"
        f"- Neural graph size: {neural_size}\n"
        f"- Duration: {elapsed:.1f}s\n"
        f"- Status: {status}\n"
    )
    try:
        with open(reconcile_log, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        rlog(f"Failed to write reconcile log: {e}", "WARNING")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Adam Framework — Sleep Cycle: merge daily logs into core memory"
    )
    parser.add_argument("--vault-path", required=True,
                        help="Path to your Vault directory")
    parser.add_argument("--api-key", default="",
                        help="Gemini API key (free at aistudio.google.com)")
    parser.add_argument("--config", default="",
                        help="Path to openclaw.json or mcporter.json to read API key from")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without modifying any files")
    parser.add_argument("--force", action="store_true",
                        help="Run even if last run was less than 6 hours ago")
    args = parser.parse_args()

    paths = resolve_paths(args.vault_path)

    rlog("=" * 60)
    rlog("Adam Framework — Sleep Cycle starting")
    rlog("=" * 60)

    if args.dry_run:
        rlog("DRY RUN MODE — no files will be modified")

    # Ensure logs dir exists
    paths["logs_dir"].mkdir(parents=True, exist_ok=True)

    # Resolve API key
    api_key = args.api_key
    if not api_key and args.config:
        api_key = get_api_key_from_config(args.config)
    if not api_key:
        # Try default openclaw.json location
        default_cfg = Path(args.vault_path).parent / ".openclaw" / "openclaw.json"
        if default_cfg.exists():
            api_key = get_api_key_from_config(str(default_cfg))
    if not api_key:
        rlog("No Gemini API key found. Provide via --api-key or --config.", "ERROR")
        rlog("Get a free key at: https://aistudio.google.com/app/apikey", "ERROR")
        sys.exit(2)

    # Part 1: State
    state       = load_state(paths["state_file"])
    unprocessed = get_unprocessed_logs(paths["logs_dir"], state)
    total       = len(unprocessed)

    if total == 0:
        rlog("Nothing to reconcile — all logs already processed.")
        write_reconcile_log(paths["reconcile_log"], [], 0, 0, 0, 0, 0, "", "SKIPPED — nothing to process")
        sys.exit(0)

    # Rolling window cap
    to_process = unprocessed[:MAX_LOGS_PER_RUN]
    deferred   = total - len(to_process)
    if deferred > 0:
        rlog(f"Processing {len(to_process)} of {total} logs. {deferred} deferred to next run.")
    else:
        rlog(f"Processing {len(to_process)} unprocessed logs.")

    # Verify core memory exists
    if not paths["core_memory"].exists():
        rlog(f"CORE_MEMORY.md not found at {paths['core_memory']}", "ERROR")
        rlog("Create it first from vault-templates/CORE_MEMORY.template.md", "ERROR")
        sys.exit(2)

    # Part 2: Backup
    if not args.dry_run:
        backup_path = backup_core_memory(paths["core_memory"], paths["backup_dir"])
        if not backup_path:
            rlog("Aborting — cannot proceed without a successful backup.", "ERROR")
            sys.exit(2)

    # Read current core memory
    try:
        with open(paths["core_memory"], "r", encoding="utf-8", errors="replace") as f:
            old_content = f.read()
        old_lines = len(old_content.splitlines())
        rlog(f"Core memory loaded: {old_lines} lines")
    except Exception as e:
        rlog(f"Cannot read CORE_MEMORY.md: {e}", "ERROR")
        sys.exit(2)

    # Build combined logs content
    logs_parts = []
    for log_file in to_process:
        log_path = paths["logs_dir"] / log_file
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                logs_parts.append(f"### {log_file}\n{f.read()}")
        except Exception as e:
            rlog(f"Could not read {log_file}: {e}", "WARNING")

    if not logs_parts:
        rlog("No log content could be read — aborting.", "ERROR")
        sys.exit(2)

    logs_content = "\n\n".join(logs_parts)
    date_range   = f"{to_process[0].replace('.md','')} to {to_process[-1].replace('.md','')}"

    rlog(f"Logs to merge: {date_range}")

    # Part 3: LLM reconciliation
    if args.dry_run:
        rlog(f"[DRY RUN] Would call Gemini to merge {len(to_process)} logs into CORE_MEMORY.md")
        rlog(f"[DRY RUN] Core memory would be updated and neural ingest would run")
        sys.exit(0)

    reconciled = call_gemini(api_key, old_content, logs_content, date_range, len(to_process))

    if not reconciled or not validate_response(reconciled, old_content):
        rlog("Reconciliation failed validation — CORE_MEMORY.md NOT modified.", "ERROR")
        rlog("Your original file is intact. Check logs above for details.", "ERROR")
        write_reconcile_log(paths["reconcile_log"], to_process, total, deferred,
                            old_lines, old_lines, 0, "LLM validation failed", "FAILED")
        sys.exit(2)
    # Part 4: Write updated core memory
    try:
        with open(paths["core_memory"], "w", encoding="utf-8") as f:
            f.write(reconciled)
        new_lines = len(reconciled.splitlines())
        rlog(f"CORE_MEMORY.md updated. {old_lines} → {new_lines} lines.")
    except Exception as e:
        rlog(f"Failed to write CORE_MEMORY.md: {e}", "ERROR")
        sys.exit(2)

    # Part 5: Vector reindex is SENTINEL's job — not this script
    rlog("Vector reindex: deferred to SENTINEL (fires after gateway health check).")

    # Part 6: Neural ingest — diff only, never nuke
    neural_count       = 0
    neural_skip_reason = ""
    try:
        neural_count = ingest_neural(old_content, reconciled)
    except Exception as e:
        neural_skip_reason = str(e)
        rlog(f"Neural ingest skipped: {e}", "WARNING")

    # Part 7: Neural metrics snapshot — query live counts and persist
    neurons, synapses = get_neural_stats()
    if neurons > 0:
        snapshot_neural_metrics(paths["vault_root"], neurons, synapses)

    # Update state
    state["processed_logs"]    = list(set(state.get("processed_logs", [])) | set(to_process))
    state["last_reconcile_run"] = datetime.now().strftime("%Y-%m-%d")
    save_state(paths["state_file"], state)

    # Part 7: Log completion
    status = "SUCCESS" if not neural_skip_reason else "PARTIAL"
    write_reconcile_log(paths["reconcile_log"], to_process, total, deferred,
                        old_lines, new_lines, neural_count, neural_skip_reason, status,
                        neurons, synapses)

    # Part 8: Update TOPIC_INDEX freshness
    try:
        update_topic_index(to_process, reconciled)
    except Exception as e:
        rlog(f"TOPIC_INDEX update skipped (non-fatal): {e}", "WARNING")

    rlog(f"Sleep cycle complete. Status: {status}")
    sys.exit(0)


def update_topic_index(processed_logs, reconciled_memory):
    """
    Update TOPIC_INDEX.md confidence scores based on recency.
    Confidence is mechanical: days since last_touched.
    Only updates confidence — does NOT rewrite last_known_state (that's Adam's job via Telegram).
    """
    TOPIC_INDEX_PATH = os.path.join(paths["vault_root"], "workspace", "TOPIC_INDEX.md")
    if not os.path.exists(TOPIC_INDEX_PATH):
        rlog("TOPIC_INDEX.md not found — skipping update.", "WARNING")
        return

    today = datetime.now().date()

    with open(TOPIC_INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    def recalc_confidence(last_touched_str, stale_after_days):
        try:
            last = datetime.strptime(last_touched_str.strip(), "%Y-%m-%d").date()
            days_since = (today - last).days
            if days_since <= 2:
                return "HIGH"
            elif days_since <= int(stale_after_days):
                return "MEDIUM"
            else:
                return "LOW"
        except Exception:
            return "LOW"

    import re as _re

    def replace_confidence(match):
        last_touched = _re.search(r"last_touched:\s*(\S+)", match.group(0))
        stale_after = _re.search(r"stale_after_days:\s*(\d+)", match.group(0))
        if not last_touched or not stale_after:
            return match.group(0)
        new_conf = recalc_confidence(last_touched.group(1), stale_after.group(1))
        return _re.sub(r"confidence:\s*\S+", f"confidence: {new_conf}", match.group(0))

    updated = _re.sub(r"(## .+?\n(?:- .+\n)*)", replace_confidence, content)

    with open(TOPIC_INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    rlog("TOPIC_INDEX.md confidence scores updated.")


if __name__ == "__main__":
    main()
