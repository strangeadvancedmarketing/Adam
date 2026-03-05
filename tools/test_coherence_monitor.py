"""
test_coherence_monitor.py — Verification suite for coherence_monitor.py
Tests run against REAL session data from the live OpenClaw sessions directory.
Does NOT touch Adam, does NOT write to AdamsVault during tests.
All output files go to a temp test directory.

Run: python tools/test_coherence_monitor.py
Pass = all assertions green. Fail = something needs fixing before implementation.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# ── PATH SETUP ────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT    = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

LIVE_SESSIONS = r"C:\Users\AJSup\.openclaw\agents\main\sessions"
TEST_SESSION  = os.path.join(
    LIVE_SESSIONS,
    "b528023e-6cac-41bc-a3c2-ac1f6638d7db.jsonl"
)

# ── TEST FIXTURES ─────────────────────────────────────────────────────────────
def make_assistant_turn(input_tokens=5000, has_scratchpad=True):
    """Build a minimal assistant turn matching OpenClaw JSONL message format."""
    content = []
    if has_scratchpad:
        content.append({
            "type": "thinking",
            "thinking": "Let me think...",
            "thinkingSignature": "reasoning_content"
        })
        content.append({
            "type": "text",
            "text": "<scratchpad>\n## 1. THINK\nAnalyzing request.\n</scratchpad>\nHere is my response."
        })
    else:
        content.append({
            "type": "text",
            "text": "Here is my response without any scratchpad."
        })
    return {
        "role": "assistant",
        "content": content,
        "usage": {
            "input": input_tokens,
            "output": 100,
            "totalTokens": input_tokens + 100
        }
    }

def make_jsonl_session(turns):
    """
    Build a minimal JSONL session string with a session header + message lines.
    Each turn is (role, input_tokens, has_scratchpad).
    """
    lines = []
    lines.append(json.dumps({
        "type": "session", "version": 3,
        "id": "test-session-001",
        "timestamp": datetime.now().isoformat()
    }))
    for role, input_tokens, has_scratchpad in turns:
        if role == "assistant":
            msg = make_assistant_turn(input_tokens, has_scratchpad)
        else:
            msg = {"role": role, "content": [{"type": "text", "text": "user message"}]}
        lines.append(json.dumps({
            "type": "message",
            "id": f"msg-{len(lines)}",
            "message": msg
        }))
    return "\n".join(lines)

# ── IMPORT MONITOR WITH PATCHED PATHS ─────────────────────────────────────────
# We import the module but patch all path constants to point at temp dirs
# so tests never touch AdamsVault or the live sessions directory.

import importlib
import coherence_monitor as cm

# ── TEST CASES ────────────────────────────────────────────────────────────────

class TestSessionFileDiscovery(unittest.TestCase):
    """Verify the live session finder works against the real sessions directory."""

    def test_finds_live_session(self):
        """find_active_session() must return a real .jsonl file path."""
        result = cm.find_active_session()
        self.assertIsNotNone(result, "Should find at least one active session")
        self.assertTrue(result.endswith(".jsonl"),
                        f"Expected .jsonl, got: {result}")
        self.assertTrue(os.path.exists(result),
                        f"Returned path does not exist: {result}")

    def test_excludes_lock_files(self):
        """Must not return .lock files."""
        result = cm.find_active_session()
        if result:
            self.assertNotIn(".lock", result)

    def test_excludes_deleted_files(self):
        """Must not return .deleted. files."""
        result = cm.find_active_session()
        if result:
            self.assertNotIn(".deleted.", result)

    def test_excludes_reset_files(self):
        """Must not return .reset. files."""
        result = cm.find_active_session()
        if result:
            self.assertNotIn(".reset.", result)


class TestJsonlParsing(unittest.TestCase):
    """Verify JSONL parser handles real session format correctly."""

    def test_reads_real_session(self):
        """read_session() must successfully parse the known test session."""
        self.assertTrue(os.path.exists(TEST_SESSION),
                        f"Test session not found: {TEST_SESSION}")
        turns, last_tokens = cm.read_session(TEST_SESSION)
        self.assertIsInstance(turns, list)
        self.assertGreater(len(turns), 0, "Should find at least one assistant turn")
        self.assertGreater(last_tokens, 0, "Should read real token count > 0")

    def test_token_count_is_real_not_estimated(self):
        """Token count must come from usage field, not char estimation."""
        turns, last_tokens = cm.read_session(TEST_SESSION)
        # The known session has input tokens around 21000-27000
        self.assertGreater(last_tokens, 1000,
                           "Tokens should be real API usage counts, not tiny")
        self.assertLess(last_tokens, cm.CONTEXT_WINDOW,
                        "Tokens should be less than context window size")

    def test_handles_malformed_lines_gracefully(self):
        """Parser must skip malformed lines without crashing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            f.write('{"type":"session","id":"x"}\n')
            f.write('THIS IS NOT JSON\n')
            f.write(json.dumps({
                "type": "message",
                "message": make_assistant_turn(5000, True)
            }) + '\n')
            tmp_path = f.name
        try:
            turns, tokens = cm.read_session(tmp_path)
            self.assertEqual(len(turns), 1)
        finally:
            os.unlink(tmp_path)

    def test_handles_empty_file(self):
        """Empty session file must return empty list without crashing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            tmp_path = f.name
        try:
            turns, tokens = cm.read_session(tmp_path)
            self.assertEqual(turns, [])
            self.assertEqual(tokens, 0)
        finally:
            os.unlink(tmp_path)


class TestScratchpadDetection(unittest.TestCase):
    """Verify scratchpad presence/absence detection logic."""

    def _turns_from_jsonl(self, jsonl_str):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            f.write(jsonl_str)
            tmp = f.name
        try:
            turns, tokens = cm.read_session(tmp)
        finally:
            os.unlink(tmp)
        return turns

    def test_detects_scratchpad_present(self):
        """Should return True when scratchpad tag is in recent turns."""
        jsonl = make_jsonl_session([
            ("user", 0, False),
            ("assistant", 5000, True),
        ])
        turns = self._turns_from_jsonl(jsonl)
        self.assertTrue(cm.check_scratchpad(turns))

    def test_detects_scratchpad_absent(self):
        """Should return False when no scratchpad in recent window."""
        jsonl = make_jsonl_session([
            ("user", 0, False),
            ("assistant", 5000, False),
            ("assistant", 6000, False),
        ])
        turns = self._turns_from_jsonl(jsonl)
        self.assertFalse(cm.check_scratchpad(turns))

    def test_window_respects_last_n_turns(self):
        """
        Scratchpad in turn 1 of 15 should NOT count when window=10.
        Only last 10 turns matter.
        """
        # 5 turns with scratchpad, then 10 turns without
        session_turns = (
            [("assistant", 2000, True)] * 5 +
            [("assistant", 3000, False)] * 10
        )
        jsonl = make_jsonl_session(
            [("user", 0, False)] + session_turns
        )
        turns = self._turns_from_jsonl(jsonl)
        result = cm.check_scratchpad(turns, window=10)
        self.assertFalse(result,
            "Scratchpad 11+ turns ago should not count within window=10")

    def test_real_session_scratchpad_check(self):
        """Run scratchpad check against real live session — must not crash."""
        turns, _ = cm.read_session(TEST_SESSION)
        # Just verify it runs and returns a bool — not asserting True/False
        # since the live session state is unknown at test time
        result = cm.check_scratchpad(turns)
        self.assertIsInstance(result, bool)


class TestDriftScoring(unittest.TestCase):
    """Verify drift score matrix covers all cases correctly."""

    def test_coherent_low_context(self):
        self.assertEqual(cm.score_drift(True, 0.2), 0.0)

    def test_scratchpad_absent_low_context(self):
        self.assertEqual(cm.score_drift(False, 0.2), 0.3)

    def test_scratchpad_present_high_context(self):
        self.assertEqual(cm.score_drift(True, 0.70), 0.4)

    def test_scratchpad_absent_mid_context(self):
        self.assertEqual(cm.score_drift(False, 0.50), 0.6)

    def test_drift_confirmed(self):
        self.assertEqual(cm.score_drift(False, 0.70), 0.9)

    def test_reanchor_triggered_at_06(self):
        self.assertTrue(cm.should_reanchor(0.6, 0.50))

    def test_reanchor_not_triggered_at_03(self):
        self.assertFalse(cm.should_reanchor(0.3, 0.20))

    def test_reanchor_triggered_by_context_alone(self):
        """High context should trigger re-anchor even if scratchpad present."""
        self.assertTrue(cm.should_reanchor(0.4, 0.70))


class TestBaselineAndLog(unittest.TestCase):
    """Verify baseline and coherence log are session-scoped and reset correctly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.baseline_path = os.path.join(self.tmpdir, "coherence_baseline.json")
        self.log_path = os.path.join(self.tmpdir, "coherence_log.json")
        # Patch paths to temp dir
        self._orig_baseline = cm.BASELINE_FILE
        self._orig_log = cm.COHERENCE_LOG
        cm.BASELINE_FILE = self.baseline_path
        cm.COHERENCE_LOG = self.log_path

    def tearDown(self):
        cm.BASELINE_FILE = self._orig_baseline
        cm.COHERENCE_LOG = self._orig_log
        shutil.rmtree(self.tmpdir)

    def test_creates_baseline_if_missing(self):
        baseline = cm.load_baseline()
        self.assertEqual(baseline["session_date"], str(date.today()))
        self.assertTrue(os.path.exists(self.baseline_path))

    def test_baseline_resets_on_new_day(self):
        """Stale baseline from yesterday must be replaced."""
        stale = {"session_date": "2000-01-01", "reinjections": 99, "drift_events": []}
        with open(self.baseline_path, "w") as f:
            json.dump(stale, f)
        baseline = cm.load_baseline()
        self.assertEqual(baseline["session_date"], str(date.today()))
        self.assertEqual(baseline["reinjections"], 0)

    def test_baseline_persists_within_day(self):
        """Baseline from today must be loaded without reset."""
        today_baseline = {
            "session_date": str(date.today()),
            "reinjections": 3,
            "drift_events": [],
            "last_check_turn": 25
        }
        with open(self.baseline_path, "w") as f:
            json.dump(today_baseline, f)
        loaded = cm.load_baseline()
        self.assertEqual(loaded["reinjections"], 3)

    def test_coherence_log_resets_on_new_day(self):
        """Stale log from yesterday must be discarded."""
        stale_log = {"session_date": "2000-01-01", "events": [{"turn": 5}]}
        with open(self.log_path, "w") as f:
            json.dump(stale_log, f)
        clog = cm.load_coherence_log()
        self.assertEqual(clog["events"], [])

    def test_coherence_log_appends_events(self):
        cm.append_coherence_event(10, 0.45, False, 0.6, "reanchor_triggered")
        cm.append_coherence_event(20, 0.55, True, 0.0, "coherent")
        with open(self.log_path) as f:
            clog = json.load(f)
        self.assertEqual(len(clog["events"]), 2)
        self.assertEqual(clog["events"][0]["action"], "reanchor_triggered")
        self.assertEqual(clog["events"][1]["action"], "coherent")


class TestReanchorTrigger(unittest.TestCase):
    """Verify re-anchor trigger file is written correctly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.trigger_path = os.path.join(self.tmpdir, "reanchor_pending.json")
        self._orig = cm.REANCHOR_TRIGGER
        cm.REANCHOR_TRIGGER = self.trigger_path

    def tearDown(self):
        cm.REANCHOR_TRIGGER = self._orig
        shutil.rmtree(self.tmpdir)

    def test_writes_trigger_file(self):
        cm.write_reanchor_trigger("test content", 42, 0.9)
        self.assertTrue(os.path.exists(self.trigger_path))
        with open(self.trigger_path) as f:
            payload = json.load(f)
        self.assertEqual(payload["turn"], 42)
        self.assertEqual(payload["drift_score"], 0.9)
        self.assertEqual(payload["consumed"], False)
        self.assertIn("test content", payload["content"])

    def test_trigger_is_valid_json(self):
        cm.write_reanchor_trigger("re-anchor me", 10, 0.6)
        with open(self.trigger_path) as f:
            data = json.load(f)  # Should not raise
        self.assertIn("content", data)


# ── RUNNER ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("coherence_monitor test suite")
    print(f"Testing against live sessions: {LIVE_SESSIONS}")
    print("=" * 60)
    unittest.main(verbosity=2)
