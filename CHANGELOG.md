# Changelog

All notable changes to the Adam Framework are documented here.

---

## [v1.1.0] — 2026-03-05

### Fixed

#### `engine/SENTINEL.template.ps1` — vector reindex hitting nonexistent HTTP endpoint

**Root cause:** The vector reindex block was calling `POST /api/memory/reindex` on
the OpenClaw gateway. That endpoint does not exist — OpenClaw exposes no REST route
for memory reindex operations. Every boot produced:

```
[SENTINEL] Vector reindex failed (non-fatal): The remote server returned an error: (405) Method Not Allowed.
```

The error was non-fatal (system continued booting) but the vector index was never
refreshed after reconcile runs, meaning new memory written by the sleep cycle was
not searchable until the next manual CLI reindex.

**Fix:** Replaced the `Invoke-WebRequest` block with a direct CLI call:
```powershell
$reindexResult = & openclaw memory index --agent main 2>&1 | Out-String
```
This is the documented OpenClaw approach (`openclaw memory index`). No HTTP call,
no auth token required, works on every platform. Confirmed clean on first boot:
```
[SENTINEL] Vector reindex triggered successfully.
```

**Applies to:** `engine/SENTINEL.template.ps1` (public template). Live SENTINEL
instances should update the reindex block to match.

---

## [v1.0.10] — 2026-03-05

### Fixed

#### `coherence_monitor.py` — score_drift fall-through causing production false positives

**Root cause:** `score_drift()` used chained independent `if` statements. No branch
covered `scratchpad_present=True` with `40% <= context_pct < 65%`. All four conditions
evaluated False and execution fell through to the final `return 0.9` catch-all —
maximum drift score — even with the scratchpad actively firing.

**Impact:** Every session above 40% context depth permanently scored as critical drift.
SENTINEL fired re-anchor injections every 5 minutes. BOOT_CONTEXT.md grew from ~21KB
to ~23KB (536 lines) with 5 appended re-anchor blocks, increasing Adam's response
latency and eventually producing gateway timeout errors.

**Fix:** Replaced chained `if` with exhaustive `if/elif/else` on `scratchpad_present`.
Added the missing branch: `scratchpad_present=True, mid-context → 0.2` (healthy pressure,
no action). Simplified `should_reanchor()` to fire only on dropout signals
(`drift_score >= 0.6`) — context depth alone no longer triggers re-anchor when
the scratchpad is active.

**Recovery applied:** BOOT_CONTEXT.md recompiled clean. Pending false-positive
re-anchor cleared. Next coherence check: exit 0, drift score 0.2.

#### `test_coherence_monitor.py` — test suite updated to cover the bug case

Added 3 new tests covering the exact failure mode and regression prevention:
- `test_scratchpad_present_mid_context` — the bug case: `score_drift(True, 0.50) == 0.2`
- `test_no_fallthrough_exhaustive` — all 6 scoring branches verified in one subTest loop
- `test_reanchor_not_triggered_by_context_alone` — replaces the now-incorrect
  `test_reanchor_triggered_by_context_alone` (old behavior was wrong)
- `test_reanchor_only_on_dropout` — verifies deep context with active scratchpad
  never fires re-anchor

**Test count: 27 → 30. All passing.**

See `docs/LESSONS_LEARNED.md` for full root cause, cascade, and recovery steps.

---

## [v1.0.9] — 2026-03-05


### 🚨 BREAKTHROUGH: Layer 5 — Within-Session Coherence Degradation Solved

The second major unsolved problem in production AI deployments is now solved.

**The problem:** As a session accumulates context, the model's reasoning consistency
and identity coherence degrade quietly — before compaction triggers, while the
conversation is still nominally "working." The model doesn't announce this. It drifts.

**The signal:** Scratchpad dropout. When Adam is coherent, the ReAct scratchpad fires
on every complex turn. When he drifts, it stops. Binary, production-validated,
zero instrumentation overhead — the system's own defined behavior is the detector.

**What shipped today:**

#### Added
- `tools/coherence_monitor.py` — 5-layer coherence monitoring system:
  - Reads live OpenClaw session JSONL (line-by-line, handles real format)
  - Token depth from `usage.input` field — not char estimation (base64 images
    in tool results inflate char counts by 10x; real API usage field does not)
  - Session file targeting: UUID `.jsonl` files only — not `sessions.json` index
  - Scratchpad detection across thinking blocks and text blocks
  - Drift scoring 0.0–1.0 across scratchpad + context depth signals
  - Re-anchor content pulled from AGENTS.md + active-context.md (~200 tokens)
  - `reanchor_pending.json` consumed flag prevents duplicate injection
  - Baseline and coherence log reset daily (no cross-session accumulation)
  - Exit codes: 0 = coherent, 1 = drift detected, 2 = error

- `tools/test_coherence_monitor.py` — 27-test verification suite:
  - All tests run against real live OpenClaw session data before touching production
  - Covers: session file discovery, JSONL parsing, scratchpad detection, drift
    scoring, baseline lifecycle, coherence log rotation, re-anchor trigger format
  - **27/27 passing** — zero failures against live data before first implementation

- `vault-templates/coherence_baseline.template.json` — session baseline schema
- `vault-templates/coherence_log.template.json` — event log schema

#### Changed
- `engine/SENTINEL.template.ps1` — Layer 5 integrated into watchdog loop:
  - `Invoke-CoherenceCheck` runs every 10 ticks (5 minutes)
  - `Invoke-ReAnchor` consumes `reanchor_pending.json`, appends to `BOOT_CONTEXT.md`,
    marks consumed — same injection path already proven at boot
  - Kokoro TTS permanently removed — Edge TTS only, no more silent restart loops
    on a dead process

- `README.md` — upgraded to 5-layer architecture; both solved problems documented
- `ROADMAP.md` — Layer 5 marked shipped; Problem Two marked solved

#### First production run
- Coherence check at 16:30:36 — exit 0, session coherent
- Re-anchor injection path confirmed functional
- SENTINEL log: `"Coherence monitor every 5 min."` on all subsequent boots



### Added
- `.github/ISSUE_TEMPLATE/bug_report.md` — structured bug report template with
  component checklist, log paste areas, and LESSONS_LEARNED cross-reference prompt
- `.github/ISSUE_TEMPLATE/setup_help.md` — setup help template with phase/step
  tracking and expected vs. actual output fields
- `.github/ISSUE_TEMPLATE/feature_request.md` — feature request template with
  explicit contributor self-identification prompt ("would you build this?")
- `.github/PULL_REQUEST_TEMPLATE.md` — PR template enforcing repo philosophy:
  tested on real hardware, no cloud dependencies, Vault files human-readable

### Changed
- `README.md` — added landing page and showcase links above the fold (first visible
  element for all visitors); added "What It Looks Like" section with real SENTINEL
  boot output and Adam's first context-aware response

---

## [v1.0.7] — 2026-03-05

### Added
- `index.html` — GitHub Pages landing page at strangeadvancedmarketing.github.io/Adam/
- `ROADMAP.md` — full roadmap: shipped features, near-term work, community
  opportunities, PersonaPlex voice upgrade research, long-term concepts
- 15 targeted GitHub repository topics for discoverability

---

## [v1.0.6] — 2026-03-05

### Added
- `docs/SKILLS_SYSTEM.md` — documentation-first plugin architecture; covers skill
  definition, activation, the four active production skills, and how to add new ones

---

## [v1.0.5] — 2026-03-05

### Added
- `docs/CONTEXT_COMPILER.md` — explains BOOT_CONTEXT.md compilation: hippocampus/
  cortex split, source priority, what gets injected vs. what stays in Vault
- `docs/SWARM.md` — multi-agent coordination via shared Vault; PATTERN_SEEKER
  architecture, task queue pattern, swarm coordination primitives
- `CONTRIBUTING.md` — contribution guide: priorities, how to contribute, what a
  good PR looks like, repo philosophy

### Fixed
- `engine/SENTINEL.template.ps1` — corrected boot sequence and mutex lock pattern
  to match production-validated implementation

---

## [v1.0.4] — 2026-03-05

### Added
- `showcase/ai-amnesia-solved.html` — interactive data visualization ("The Proof")
  rendering 353-session development arc as charts; V3 with full timeline,
  neural growth, session velocity, and key milestone markers

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
