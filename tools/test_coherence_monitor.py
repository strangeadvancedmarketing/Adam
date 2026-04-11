"""
test_coherence_monitor.py — Verification suite for coherence_monitor.py v2.0
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
def make_assistant_turn(input_tokens: int = 5000, model: str = "test-model") -> dict:
    """Build a minimal assistant turn matching OpenClaw JSONL message format."""
    return {
        "role": "assistant",
        "content": [{"type": "text", "text": "Here is my response."}],
        "model": model,
        "usage": {
            "input": input_tokens,
            "output": 100,
            "totalTokens": input_tokens + 100
        }
    }

def make_jsonl_session(turns: list[tuple]) -> str:
    """
    Build a minimal JSONL session string with a session header + message lines.
    Each turn is (role, input_tokens).
    """
    lines = []
    lines.append(json.dumps({
        "type": "session", "version": 3,
        "id": "test-session-001",
        "timestamp": datetime.now().isoformat()
    }))
    for role, input_tokens in turns:
        if role == "assistant":
            msg = make_assistant_turn(input_tokens)
        else:
            msg = {"role": role, "content": [{"type": "text", "text": "user message"}]}
        lines.append(json.dumps({
            "type": "message",
            "id": f"msg-{len(lines)}",
            "message": msg
        }))
    return "\n".join(lines)

# ── IMPORT MONITOR WITH PATCHED PATHS ─────────────────────────────────────────
import importlib
import coherence_monitor as cm

# ── TEST CASES ────────────────────────────────────────────────────────────────

@unittest.skipUnless(os.path.exists(LIVE_SESSIONS), "Skipped: live sessions directory not present (CI environment)")
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


@unittest.skipUnless(os.path.exists(TEST_SESSION), "Skipped: live session file not present (CI environment)")
class TestJsonlParsing(unittest.TestCase):
    """Verify JSONL parser handles real session format correctly."""

    def test_reads_real_session(self):
        """read_session() must successfully parse the known test session."""
        self.assertTrue(os.path.exists(TEST_SESSION),
                        f"Test session not found: {TEST_SESSION}")
        turn_count, last_tokens, model_id = cm.read_session(TEST_SESSION)
        self.assertIsInstance(turn_count, int)
        self.assertGreater(turn_count, 0, "Should find at least one assistant turn")
        self.assertGreater(last_tokens, 0, "Should read real token count > 0")
        self.assertIsInstance(model_id, str)

    def test_token_count_is_real_not_estimated(self):
        """Token count must come from usage field, not char estimation."""
        turn_count, last_tokens, model_id = cm.read_session(TEST_SESSION)
        self.assertGreater(last_tokens, 1000,
                           "Tokens should be real API usage counts, not tiny")
        self.assertLess(last_tokens, cm.CONTEXT_WINDOW,
                        "Tokens should be less than context window size")


class TestJsonlParsingWithFixtures(unittest.TestCase):
    """Verify JSONL parser with synthetic fixtures (runs in CI)."""

    def _read_from_jsonl(self, jsonl_str: str) -> tuple:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            f.write(jsonl_str)
            tmp = f.name
        try:
            return cm.read_session(tmp)
        finally:
            os.unlink(tmp)

    def test_counts_assistant_turns(self):
        """read_session() must return correct turn count."""
        jsonl = make_jsonl_session([
            ("user", 0),
            ("assistant", 5000),
            ("user", 0),
            ("assistant", 8000),
        ])
        turn_count, last_tokens, model_id = self._read_from_jsonl(jsonl)
        self.assertEqual(turn_count, 2)
        self.assertEqual(last_tokens, 8000)

    def test_returns_model_id(self):
        """read_session() must return the model from the last assistant turn."""
        jsonl = make_jsonl_session([
            ("user", 0),
            ("assistant", 5000),
        ])
        turn_count, last_tokens, model_id = self._read_from_jsonl(jsonl)
        self.assertEqual(model_id, "test-model")

    def test_handles_malformed_lines_gracefully(self):
        """Parser must skip malformed lines without crashing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            f.write('{"type":"session","id":"x"}\n')
            f.write('THIS IS NOT JSON\n')
            f.write(json.dumps({
                "type": "message",
                "message": make_assistant_turn(5000)
            }) + '\n')
            tmp_path = f.name
        try:
            turn_count, tokens, model_id = cm.read_session(tmp_path)
            self.assertEqual(turn_count, 1)
        finally:
            os.unlink(tmp_path)

    def test_handles_empty_file(self):
        """Empty session file must return zeros without crashing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            tmp_path = f.name
        try:
            turn_count, tokens, model_id = cm.read_session(tmp_path)
            self.assertEqual(turn_count, 0)
            self.assertEqual(tokens, 0)
            self.assertEqual(model_id, "unknown")
        finally:
            os.unlink(tmp_path)


class TestDriftScoring(unittest.TestCase):
    """Verify v2.0 drift score based on token depth only."""

    def test_healthy_low_context(self):
        """Below 50% context = 0.0 (healthy)."""
        self.assertEqual(cm.score_drift(0.2), 0.0)
        self.assertEqual(cm.score_drift(0.49), 0.0)

    def test_moderate_pressure(self):
        """50-70% context = 0.3 (moderate pressure)."""
        self.assertEqual(cm.score_drift(0.50), 0.3)
        self.assertEqual(cm.score_drift(0.65), 0.3)

    def test_high_pressure(self):
        """70-85% context = 0.7 (high pressure, re-anchor)."""
        self.assertEqual(cm.score_drift(0.70), 0.7)
        self.assertEqual(cm.score_drift(0.80), 0.7)

    def test_critical(self):
        """Above 85% context = 0.9 (critical)."""
        self.assertEqual(cm.score_drift(0.85), 0.9)
        self.assertEqual(cm.score_drift(0.99), 0.9)

    def test_reanchor_triggered_at_07(self):
        """Re-anchor fires at score >= 0.7."""
        self.assertTrue(cm.should_reanchor(0.7))
        self.assertTrue(cm.should_reanchor(0.9))

    def test_reanchor_not_triggered_below_07(self):
        """Re-anchor does not fire below 0.7."""
        self.assertFalse(cm.should_reanchor(0.0))
        self.assertFalse(cm.should_reanchor(0.3))

    def test_all_thresholds_exhaustive(self):
        """All 4 scoring bands return expected scores."""
        cases = [
            (0.10, 0.0),   # healthy
            (0.50, 0.3),   # moderate
            (0.70, 0.7),   # high pressure
            (0.85, 0.9),   # critical
        ]
        for pct, expected in cases:
            with self.subTest(context=pct):
                self.assertEqual(cm.score_drift(pct), expected)


class TestBaselineAndLog(unittest.TestCase):
    """Verify baseline and coherence log are session-scoped and reset correctly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.baseline_path = os.path.join(self.tmpdir, "coherence_baseline.json")
        self.log_path = os.path.join(self.tmpdir, "coherence_log.json")
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
            "last_check_turn": 25,
            "session_start": datetime.now().isoformat(),
            "scratchpad_expected": True,
            "context_window": cm.CONTEXT_WINDOW
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
        """v2.0 event format: (turn, context_pct, drift_score, action, model_id)"""
        cm.append_coherence_event(10, 0.75, 0.7, "reanchor_triggered", "kimi-k2.5")
        cm.append_coherence_event(20, 0.45, 0.0, "healthy", "kimi-k2.5")
        with open(self.log_path) as f:
            clog = json.load(f)
        self.assertEqual(len(clog["events"]), 2)
        self.assertEqual(clog["events"][0]["action"], "reanchor_triggered")
        self.assertEqual(clog["events"][0]["drift_score"], 0.7)
        self.assertEqual(clog["events"][0]["model"], "kimi-k2.5")
        self.assertEqual(clog["events"][1]["action"], "healthy")


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
        cm.write_reanchor_trigger("re-anchor me", 10, 0.7)
        with open(self.trigger_path) as f:
            data = json.load(f)  # Should not raise
        self.assertIn("content", data)

    def test_deduplication_skips_unconsumed_pending(self):
        """
        If reanchor_pending.json already exists with consumed=false,
        write_reanchor_trigger must NOT overwrite it.
        """
        first_written = cm.write_reanchor_trigger("first re-anchor", 30, 0.7)
        self.assertTrue(first_written, "First write should succeed")

        second_written = cm.write_reanchor_trigger("second re-anchor", 35, 0.9)
        self.assertFalse(second_written, "Second write should be skipped — first still pending")

        with open(self.trigger_path) as f:
            payload = json.load(f)
        self.assertEqual(payload["turn"], 30, "File must not have been overwritten")
        self.assertIn("first re-anchor", payload["content"])

    def test_deduplication_allows_write_after_consumed(self):
        """Once consumed=true is set, the next write must succeed."""
        cm.write_reanchor_trigger("first re-anchor", 30, 0.7)
        with open(self.trigger_path, "r") as f:
            payload = json.load(f)
        payload["consumed"] = True
        with open(self.trigger_path, "w") as f:
            json.dump(payload, f)

        result = cm.write_reanchor_trigger("second re-anchor", 50, 0.9)
        self.assertTrue(result, "Write after consumed=true must succeed")
        with open(self.trigger_path) as f:
            new_payload = json.load(f)
        self.assertEqual(new_payload["turn"], 50)

    def test_reanchor_content_has_no_scratchpad_tag(self):
        """
        build_reanchor_content() must never include the literal string '<scratchpad>'
        in its output.
        """
        tmpdir = tempfile.mkdtemp()
        fake_context = os.path.join(tmpdir, "active-context.md")

        with open(fake_context, "w", encoding="utf-8") as f:
            f.write("## \U0001f525 Priority 1: TurfTracker\nFind leads.")

        orig_context = cm.ACTIVE_CONTEXT
        cm.ACTIVE_CONTEXT = fake_context
        try:
            content = cm.build_reanchor_content()
            self.assertNotIn(
                "<scratchpad>", content,
                "Re-anchor content must not contain the literal <scratchpad> tag"
            )
            # v2.0: Should contain priority context, not ReAct instructions
            self.assertIn("CONTEXT PRESSURE", content)
            self.assertIn("TurfTracker", content)
        finally:
            cm.ACTIVE_CONTEXT = orig_context
            shutil.rmtree(tmpdir)

    def test_reanchor_fallback_when_no_context_file(self):
        """build_reanchor_content() must return a fallback when active-context.md is missing."""
        orig_context = cm.ACTIVE_CONTEXT
        cm.ACTIVE_CONTEXT = "/nonexistent/path/active-context.md"
        try:
            content = cm.build_reanchor_content()
            self.assertIn("CONTEXT PRESSURE", content)
        finally:
            cm.ACTIVE_CONTEXT = orig_context


# ── RUNNER ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("coherence_monitor v2.0 test suite")
    print(f"Testing against live sessions: {LIVE_SESSIONS}")
    print("=" * 60)
    unittest.main(verbosity=2)
