# Changelog

All notable changes to the Adam Framework are documented here.

---

## [v1.0.3] — 2026-03-05

### Fixed
- **Root cause of `session-store` rename failures fully identified and resolved**
  The rename errors persisted after the v1.0.2 config fix, pointing to a second
  independent issue. Process handle inspection (via Sysinternals handle64) identified
  the actual culprit: the Claude desktop app (PID 1076) was holding two persistent
  file handles on `sessions.json` via the Desktop Commander MCP filesystem integration.
  Windows blocks atomic rename operations when any process holds the destination file open.
  
  **Fix:** Removed `C:\Users\AJSup\.openclaw\agents` from Desktop Commander's
  `allowedDirectories` config. The MCP client can no longer open files in the sessions
  directory, so no handles are acquired. Rename operations now succeed cleanly.

- **Corrected LESSONS_LEARNED entry for session-store rename errors**
  Previous entry incorrectly attributed the rename failures solely to the config reload
  loop. The reload loop was one contributing factor, but the persistent rename failures
  were independently caused by MCP filesystem handle retention. Both root causes are now
  documented accurately.

### Added
- `docs/LESSONS_LEARNED.md` updated with the MCP handle contention entry

---

## [v1.0.2] — 2026-03-05

### Fixed
- **CRITICAL: Removed invalid `contacts` key from `channels.telegram` config block**
  The `contacts` field is not a valid key in the OpenClaw `channels.telegram` schema.
  Its presence caused every hot-reload of `openclaw.json` to fail silently with:
  `Invalid config: channels.telegram: Unrecognized key: "contacts"`
  This manifested downstream as cascading `[session-store] rename failed after 5 attempts`
  errors on every session write — the gateway was stuck in a broken reload loop.

- **Heartbeat routing now uses the correct schema**
  Heartbeat delivery target is now configured via `agents.defaults.heartbeat.to` using
  the format `CHAT_ID:topic:THREAD_ID` — the documented OpenClaw approach.
  Previously attempted via undocumented `channels.telegram.contacts` alias (incorrect).

- **Updated `engine/openclaw.template.json`**
  Template now reflects the correct heartbeat configuration pattern with
  `agents.defaults.heartbeat` including `target`, `to`, and `activeHours` fields.
  Removed the invalid `contacts` block from the template entirely.

### Added
- `docs/LESSONS_LEARNED.md` — documents failure modes encountered in production
  with root causes, symptoms, and confirmed fixes. Intended to short-circuit
  debugging time for anyone running this framework.

---

## [v1.0.1] — 2026-03-05

### Fixed
- Added missing `GEMINI_API_KEY` to `env` block in `engine/openclaw.template.json`
  (was absent, causing the nightly reconciliation sleep cycle to skip Gemini consolidation silently)
- Added heartbeat `contacts` routing to template (superseded by v1.0.2 fix above)
- Fixed box-drawing character corruption artifacts in `showcase/ai-amnesia-solved.html`

### Added
- `SETUP_HUMAN.md` — step-by-step human installation guide
- `SETUP_AI.md` — agent-delegated installation guide
- `CHANGELOG.md` — this file

---

## [v1.0.0] — 2026-03-04

### Initial public release

- 4-layer persistent memory architecture: Vault injection, MCP memory search,
  neural graph (7,211 neurons / 29,291 synapses), nightly Gemini reconciliation
- `engine/openclaw.template.json` — sanitized gateway config with all placeholders
- `engine/SENTINEL.template.ps1` — watchdog, auto-start, sleep cycle scheduler
- `engine/mcporter.template.json` — MCP server wiring
- `vault-templates/` — SOUL, CORE_MEMORY, BOOT_SEQUENCE, active-context templates
- `tools/legacy_importer.py` — extract facts from Claude/ChatGPT export
- `tools/ingest_triples.ps1` — feed extracted facts into neural graph
- `tools/reconcile_memory.py` — nightly sleep cycle runner
- `docs/ARCHITECTURE.md` — deep dive on all 4 layers
- `docs/CONFIG_REFERENCE.md` — every config field explained
- `docs/PROOF.md` — 353-session production proof of work
- `showcase/ai-amnesia-solved.html` — interactive data visualization
