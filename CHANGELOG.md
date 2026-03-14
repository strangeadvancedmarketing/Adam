# Changelog

All notable changes to the Adam Framework are documented here.

## [2026.3] — March 2026

### Added
- Gumroad product line: 11 vertical-specific Adam editions live (Deal Shadow, Startup Founder, Real Estate Closer, Rainmaker, M&A Sentinel, Remote Lead, Creative Director, Product Visionary, Nonprofit Catalyst, Solo Agency Owner, Executive Coach)
- `adam-hub.html` — hub page for vertical selection ("Which Adam is right for you?")
- `generate_obsidian_links.py` — Obsidian graph generator from nmem neural graph
- `FOR_AI_VISITORS.md` — context file written specifically for AI agents reading the repo
- OpenClaw skills PR (#152) submitted to canonical skills registry

### Fixed
- Correct Gumroad badge URL (bjvnas slug)
- Template configs corrected; memory_search/tool resolution bug documented in LESSONS_LEARNED.md
- AdamsVault renamed from `C:\Adam's Vault` to `C:\AdamsVault` — apostrophe eliminated across 52 files

### Changed
- Neural graph: 16,200 neurons / 47,871 synapses (from 12,393 / 40,532)
- OpenClaw updated to 2026.3.2

---

## [2026.2] — February 2026

### Added
- Layer 5 coherence monitor (`coherence_monitor.py`) — 33/33 tests passing on live data
- `reconcile_memory.py` nightly sleep cycle (Gemini-powered consolidation)
- memory-core plugin enabled — gives Adam `memory_search` and `memory_get` mid-session
- Hybrid vector + text search (BM25 + vector, 70/30 split)
- SENTINEL.ps1 watchdog — auto-restart, sleep cycle, boot context compilation
- Session 000 seeding workflow (`legacy_importer.py` + `ingest_triples.ps1`)
- Complete nuclear reset survived Feb 14–16, 2026 — identity restored in under an hour

### Fixed
- Gateway silent failure on bad config (documented in LESSONS_LEARNED.md)
- Kokoro TTS crashes resolved by migrating to Edge TTS

---

## [2026.1] — January 2026

### Added
- Initial 5-layer architecture design and implementation
- Layer 1: Vault injection via SENTINEL bootstrap
- Layer 2: memory-core plugin (memory_search / memory_get)
- Layer 3: nmem neural graph (SQLite, associative recall)
- Layer 4: nightly reconciliation prototype
- SOUL.md / CORE_MEMORY.md / BOOT_CONTEXT.md vault template system
- SETUP_HUMAN.md and SETUP_AI.md dual onboarding paths
- adam-skills companion repo with 8 skills (weather, news, email-intelligence, inner-eye, etc.)

---

## [2025.7–12] — July–December 2025

### Foundation
- Project inception: solving AI amnesia for production business use
- 353 sessions across 8 months of development
- 6,619 message turns logged
- 4 model migrations survived
- Three-AI methodology established: Claude (builder), Gemini (philosopher), Jereme (orchestrator)
