# Changelog

All notable changes to the Adam Framework are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.1] - 2026-03-05

### Fixed
- **Sleep cycle now fully operational** — `GEMINI_API_KEY` was missing from `openclaw.template.json` env block, causing SENTINEL to silently skip nightly memory consolidation. Added to template and documented in both setup guides.
- **Telegram delivery routing** — Added `contacts` block example to `openclaw.template.json` channels section. Named destinations (e.g. `heartbeat`) now resolve correctly instead of throwing `chat not found` errors.
- **HTML showcase encoding** — Removed character encoding corruption (box-drawing artifacts in CSS section comments) from `showcase/ai-amnesia-solved.html`. File now renders cleanly across all browsers and systems.

### Improved
- `openclaw.template.json` — `GEMINI_API_KEY` added to env block. `contacts` example added to Telegram channel config. Timestamp updated.
- README — minor copy improvements.

---

## [1.0.0] - 2026-03-03

### Added
- **Complete 4-layer framework** — bootstrap vault injection, mid-session memory search via MCP, neural graph with Hebbian decay and spreading activation, nightly Gemini reconciliation.
- **`SETUP_HUMAN.md`** — Full 60-minute human setup guide. Covers Vault creation, identity file setup, SENTINEL configuration, neural memory install, Telegram integration, and legacy conversation import (Session 000).
- **`SETUP_AI.md`** — Agent-delegated setup path. AI reads the guide and configures itself. Designed for operators who want zero manual config.
- **`engine/SENTINEL.template.ps1`** — Watchdog script. Handles process cleanup, date injection, BOOT_CONTEXT compilation, gateway launch, optional Kokoro TTS, sleep cycle gate (6-hour check), vector reindex handoff, and watchdog loop with 30s heartbeat.
- **`engine/openclaw.template.json`** — Full OpenClaw config reference with all fields documented. Covers models, memory search, compaction/memoryFlush, TTS, Telegram, gateway auth, and plugin slots.
- **`engine/mcporter.template.json`** — MCP server router config template. Covers neural-memory, Gemini, Firecrawl, Notion, and OpenRouter.
- **`tools/legacy_importer.py`** — Imports existing Claude/ChatGPT/Gemini conversation exports. Regex-extracts factual triples, deduplicates, and writes to `Session_000.md` as a permanent memory foundation.
- **`tools/ingest_triples.ps1`** — PowerShell ingestion pipeline for extracted triples into the neural graph.
- **`tools/reconcile_memory.py`** — Sleep cycle script. Merges daily session logs into `CORE_MEMORY.md` via Gemini, incrementally ingests new facts into the neural graph (diff-only, no full rebuild), defers vector reindex to SENTINEL. Full CLI with `--vault-path`, `--api-key`, `--config`, `--dry-run`, and `--force` flags.
- **`vault-templates/SOUL.template.md`** — Identity foundation file. AI reads this at every boot to know who it is and who it serves.
- **`vault-templates/CORE_MEMORY.template.md`** — Living knowledge base template. Gets updated nightly by the sleep cycle.
- **`vault-templates/BOOT_SEQUENCE.md`** — Deterministic boot instructions compiled into BOOT_CONTEXT.md by SENTINEL.
- **`vault-templates/active-context.template.md`** — Current project state tracking file.
- **`docs/ARCHITECTURE.md`** — Technical deep-dive into all 4 memory layers, data flow, and component interactions.
- **`docs/CONFIG_REFERENCE.md`** — Full reference for all configuration options across openclaw.json, mcporter.json, and SENTINEL.
- **`docs/PROOF.md`** — Evidence section. 353 sessions, 7,211 neurons, 29,291 synapses, verified via SQLite. Quantitative failure taxonomy and recovery metrics.
- **`docs/SETUP.md`** — Quick-reference setup guide (condensed version of SETUP_HUMAN.md).
- **`showcase/ai-amnesia-solved.html`** — 45KB standalone HTML showcase. Full proof-of-concept presentation of the "AI amnesia — Solved" thesis. Self-contained, no build step.
- **`.github/workflows/deploy-showcase.yml`** — GitHub Pages auto-deploy for the showcase HTML.
- **`CONTRIBUTING.md`** — Contribution guidelines.

### Architecture
The framework is built around the "Bring Your Own Hippocampus" model:
- **Hippocampus** = Adam (this framework) — persistent memory OS, model-agnostic
- **Cortex** = the LLM (Kimi, Llama, Claude, GPT — interchangeable)
- **Context Compiler** = `generate_context_brief` — the handoff mechanism that summarizes memory state for any new LLM session

Built and proven over 30 days, 353 sessions, with no prior coding background.

---

[1.0.1]: https://github.com/strangeadvancedmarketing/adam/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/strangeadvancedmarketing/adam/releases/tag/v1.0.0
