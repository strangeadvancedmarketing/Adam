# Changelog

All notable changes to the Adam Framework are documented here.

Format: `[version] — date — description`

---

## [v1.0-stable] — 2026-03-06

**Full system audit. All 5 layers verified operational.**

### Added
- `AUDIT.md` — full system audit results (5 layers, 33/33 tests, paths, disk state)
- `CHANGELOG.md` — this file
- `LICENSE` — MIT license file (was in README badge only, now properly detected by GitHub)
- `TOPIC_INDEX.template.md` — populated with correct schema (was empty at launch)
- `reconcile_memory.py` Part 8 — TOPIC_INDEX confidence auto-update (HIGH/MEDIUM/LOW based on last_touched age)

### Fixed
- TOPIC_INDEX.template.md was committed empty — now contains full schema with placeholders
- AdamsVault migrated from F: to C: drive on reference machine — all SENTINEL paths confirmed clean

### Verified
- coherence_monitor test suite: 33/33 passing
- All 31 documented repo files present and populated
- Layer 5 coherence monitor active against live session data

---

## [v0.9-showcase] — 2026-03-05

**Public showcase launch.**

### Added
- `SHOWCASE.md` — community deployments, add yours
- `showcase/ai-amnesia-solved.html` — interactive data visualization (353 sessions, 6,619 turns)
- GitHub Pages deployment via `.github/workflows/deploy.yml`
- GitHub Discussions enabled
- Roadmap issue pinned
- Linux/macOS SENTINEL port marked as good first issue

### Fixed
- Narrative consistency pass across all docs (405 fix)

---

## [v0.8-public] — 2026-03-03

**Initial public release.**

### Added
- Full 5-layer architecture documented and templated
- `SETUP_HUMAN.md` + `SETUP_AI.md` — dual onboarding paths
- `engine/` — SENTINEL, gateway config, mcporter templates
- `vault-templates/` — SOUL, CORE_MEMORY, BOOT_SEQUENCE, coherence schemas, active-context
- `tools/` — legacy_importer, ingest_triples, reconcile_memory, coherence_monitor, test suite
- `docs/` — ARCHITECTURE, CONFIG_REFERENCE, PROOF, SETUP, CONTEXT_COMPILER, SWARM, SKILLS_SYSTEM, LESSONS_LEARNED, LINEAGE, LINEAGE_EXTENDED
- `CONTRIBUTING.md`, `ROADMAP.md`
- 19 GitHub topics for discoverability

## [v1.1.1] — 2026-03-08

**Production bug fixes caught by fresh-eyes repo audit.**

### Fixed
- `engine/openclaw.template.json` — `channels.telegram.streamMode` renamed to `streaming` (deprecated key)
- `engine/openclaw.template.json` — `messages.tts.auto` changed from `"always"` to `"tagged"` (prevents Telegram 429 rate limit cascade on new installs)
- `engine/SENTINEL.template.ps1` — coherence check log messages aligned to match live system output (`"Coherence check: exit 0"` / `"Coherence check: drift detected"`)
- `docs/CONFIG_REFERENCE.md` — TTS example updated to `"tagged"`, added explicit warning against `"always"`, added `streaming` key to Telegram example with deprecation note
- `README.md` — boot log example corrected to match actual SENTINEL output
- `SETUP_HUMAN.md` + `SETUP_AI.md` — added troubleshooting entry for `skills` key crash loop (gateway exits immediately with `Config invalid: Unrecognized key`)
- GitHub repo About description updated from "4-layer" to "5-layer" (was showing stale info in link previews)

### Added
- `docs/LESSONS_LEARNED.md` — full entry for 2026-03-08 `skills` key crash loop: symptom, root cause, stderr capture diagnostic, fix, and key insight

