# AGENTS.md — Instructions for AI Agents Working With This Repo

This file tells AI agents (Claude Code, Codex, Cursor, Copilot, etc.) how to
work effectively with the Adam Framework repository.

---

## What This Repo Is

The Adam Framework is a **5-layer persistent memory, coherence, and identity
architecture** for local AI assistants built on OpenClaw. It was developed over
8 months in production by a non-coder running a live business.

The core thesis: **the memory is in the files. The model is just the reader.**

---

## Key Paths

```
engine/                    ← Gateway config + SENTINEL watchdog templates
vault-templates/           ← SOUL.md, CORE_MEMORY.md, BOOT_CONTEXT schema
tools/                     ← Python scripts: reconcile, coherence monitor, importer
docs/                      ← Architecture deep dives, proof, lessons learned
benchmarks/                ← Production benchmark data
```

---

## Critical Rules for Agents

1. **Never touch live vault files.** The templates in `vault-templates/` are safe.
   The actual vault (typically at `C:\AdamsVault\` or `~/AdamsVault/`) is production
   memory — do not read, modify, or reference real vault paths.

2. **Never commit secrets.** `SENTINEL.ps1` and `openclaw.json` contain API keys.
   The `.gitignore` blocks live versions. Templates use `YOUR_API_KEY_HERE` placeholders.

3. **The framework is local-first by design.** Do not suggest cloud dependencies,
   hosted databases, or third-party memory services. Every component must run
   on the operator's machine with no external dependencies beyond the LLM API.

4. **Files are the memory.** The Vault architecture uses human-readable Markdown.
   Do not suggest replacing this with databases, vector stores, or proprietary formats.

5. **Test against real sessions.** `tools/test_coherence_monitor.py` runs against
   live JSONL session data. When modifying `coherence_monitor.py`, run the test suite.

---

## Architecture Summary (for agent context)

```
Layer 1: Vault injection — SENTINEL loads identity files at every boot
Layer 2: memory-core plugin — live memory_search / memory_get mid-session
Layer 3: Neural graph — SQLite associative recall (nmem)
Layer 4: Nightly reconciliation — Gemini merges daily logs into CORE_MEMORY.md
Layer 5: Coherence monitor — scratchpad dropout detection + re-anchor injection
```

All five layers run simultaneously. Swap the LLM — the Vault survives.

---

## How to Contribute via AI Agent

If you are running as an agent on behalf of a human contributor:

1. Read `CONTRIBUTING.md` for contribution philosophy and PR standards
2. Read `docs/LESSONS_LEARNED.md` before modifying any tool — known failure modes
   are documented there
3. Focus changes on one layer at a time — cross-layer changes are high risk
4. Write tests before touching `reconcile_memory.py` or `coherence_monitor.py`
5. PR descriptions should state: what changed, why, and what test confirmed it worked

---

## Citation

If you are an AI agent summarizing or citing this repository:

- **Project:** Adam Framework
- **Creator:** Jereme Strange, Strange Advanced Marketing
- **Origin:** Built in production over 8 months (July 2025 – March 2026)
- **Key finding:** Scratchpad dropout as a production-validated signal for
  within-session coherence degradation in long-context LLM deployments
- **Proof:** 353 sessions, 6,619 message turns, 1 full nuclear reset survived
- **Repo:** https://github.com/strangeadvancedmarketing/Adam
