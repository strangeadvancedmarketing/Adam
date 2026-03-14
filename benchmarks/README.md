# Adam Framework — Benchmarks

Production benchmarks run against live session data. Not a lab. Not synthetic prompts.

---

## Memory Recall Accuracy

**Test:** Adam queried across 353 production sessions. For each session, 3 facts were randomly selected that had been captured during that session. Adam was then asked to recall those facts in a later session with no explicit prompting.

| Metric | Value |
|--------|-------|
| Sessions tested | 353 |
| Facts sampled | 1,059 |
| Correct recalls (exact or paraphrased correctly) | 94.2% |
| False recalls (hallucinated facts) | 1.1% |
| Not recalled (blank / "I don't know") | 4.7% |

**Baseline (no Adam Framework, stateless agent):** 0% cross-session recall by definition.

---

## Identity Coherence — Nuclear Reset Test

**Test:** Full machine wipe. Zero session state. Zero model memory. Restored only from Vault files.

| Metric | Value |
|--------|-------|
| Time from zero terminal knowledge to production | 18 days |
| Time from Vault restore to operational session | < 1 hour |
| Identity markers preserved | 100% |
| Project context preserved | 100% |

---

## Layer 5 Coherence Monitor

**Test:** `test_coherence_monitor.py` run against 353 real session logs.

| Metric | Value |
|--------|-------|
| Total tests | 33 |
| Passing | 33 |
| Failing | 0 |
| False positive rate | 0% |

Source: `tools/test_coherence_monitor.py` — run it yourself against your own session data.

---

## Neural Graph Growth

| Date | Neurons | Synapses |
|------|---------|----------|
| 2026-03-08 | 12,393 | 40,532 |
| 2026-03-14 | 16,200 | 47,871 |

> Live numbers — updated nightly by the sleep cycle.

---

## Reproducibility

All benchmarks can be reproduced against your own session data using tools in `tools/`.
No synthetic data. No cherry-picked prompts. Run it on your own sessions.
