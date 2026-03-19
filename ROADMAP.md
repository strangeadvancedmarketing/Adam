# Roadmap

> What's built, what's in progress, and where this is going.
> Updated as things ship. No vaporware.

---

## Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ | Shipped and in production |
| 🔄 | In progress |
| 📋 | Planned, scoped |
| 💡 | Concept, not yet scoped |

---

## Foundation (Shipped ✅)

The core framework is complete and production-validated.

- ✅ **5-layer memory and coherence architecture** — Vault injection, session search, neural graph, nightly reconciliation, coherence monitor
- ✅ **Layer 5: Coherence monitor** — scratchpad dropout detection, real token depth tracking, auto re-anchor via BOOT_CONTEXT injection. Within-session coherence degradation: solved.
- ✅ **SENTINEL watchdog** — boot sequence, date injection, BOOT_CONTEXT compilation, auto-restart, sleep cycle, coherence check every 5 min, deferred vector reindex, mcporter daemon keep-alive
- ✅ **Neural graph integration** — 16,200 neurons / 47,874 synapses, live and growing. neural-memory v4.12.0.
- ✅ **Legacy importer** — extract facts from Claude and ChatGPT export zips, seed neural graph before Session 000
- ✅ **Nightly reconcile** — Gemini merges daily logs into CORE_MEMORY.md, incremental neural ingest, metrics snapshot
- ✅ **Skills system** — documentation-first plugin architecture, active skills in production
- ✅ **Telegram interface** — full bidirectional conversation, voice via Edge TTS, heartbeat routing
- ✅ **Email intelligence** — proactive inbox triage, urgency scoring, Telegram alerts
- ✅ **Contractor prospector** — lead discovery, demo site generation, GitHub Pages deploy, outreach
- ✅ **Context compiler** — AI-to-AI handoff with memory injection and structured return parsing
- ✅ **Nuclear reset validated** — system wiped and rebuilt, identity survived via Vault files
- ✅ **`memory_search` / `memory_get` — permanently fixed** — root cause identified and patched in `extensions/memory-core/index.ts`. Native OpenClaw memory tools now bind in every session. Full writeup in LESSONS_LEARNED.md.
- ✅ **adam-mcp PyPI package** — MCP server exposing Adam's vault memory as tools (`memory_search`, `memory_get`, `memory_list`) to Claude Desktop and any MCP-compatible client
- ✅ **ClawHub published** — `adam-framework@1.0.1` live at ClawHub registry
- ✅ **MCP Registry listing** — `io.github.strangeadvancedmarketing/adam-framework` live
- ✅ **Linux / macOS port of SENTINEL** — `engine/SENTINEL.template.sh` + `tools/ingest_triples.sh` + `engine/com.adamframework.sentinel.plist`

---

## Near Term 🔄 📋

Work in active progress or immediately next.

### Gumroad vertical products — complete the lineup
- ✅ 11 products live: Deal Shadow, Startup Founder, Real Estate Closer, Rainmaker, M&A Sentinel, Remote Lead, Creative Director, Product Visionary, Nonprofit Catalyst, Solo Agency Owner, Executive Coach
- 📋 7 remaining: GovCon Sentinel, Talent Scout, The Ghost, Shadow Researcher, Health Sovereign, Legacy Keeper, The Mastermind
- 📋 Full UX audit after all 18 are live — banner images missing on all new listings

### Neural metrics visualizer
- 📋 `showcase/neural-growth.html` — chart that reads `workspace/neural_metrics.json`
  and plots neuron/synapse growth over time. Makes the "live growing system" story
  visible to anyone who visits the repo.

### `reconcile_memory.py` test coverage
- 📋 pytest suite covering state management, backup logic, LLM validation, and
  the neural diff ingest. Makes the core tool safer to iterate on.

### openclaw update patch guard
- 📋 Post-install script that re-applies the `api.config` patch to `memory-core/index.ts`
  after every `npm update openclaw`. Currently documented in LESSONS_LEARNED.md —
  should be automated so it can't be silently lost on update.

---

## Community Opportunities 💡

High-value contributions that need someone to pick them up.

### Additional model provider templates
`openclaw.template.json` is wired for NVIDIA. Config blocks for OpenRouter, Groq,
Ollama, and Anthropic would remove the biggest setup friction for non-NVIDIA users.

### `legacy_importer.py` — additional export formats
Currently handles Claude and ChatGPT. Gemini, Perplexity, and Character.ai export
support would broaden the Session 000 seeding story.

### Obsidian plugin
The Vault is already Obsidian-compatible Markdown. A plugin that surfaces neural
graph connections and reconcile history inside Obsidian would make the framework
significantly more accessible to the Obsidian community (large, technical, aligned).

### OpenClaw plugin API documentation
The `api.config` vs `ctx.config` distinction in OpenClaw's plugin API is undocumented
and has bitten at least one production deployment (this one — see LESSONS_LEARNED.md
2026-03-19). A contribution to OpenClaw's docs clarifying the plugin context object
fields would help the broader OpenClaw community.

---

## Voice Layer Upgrade — NVIDIA PersonaPlex 💡

Worth tracking closely. Not ready to integrate yet — two hard prerequisites are
missing. Fully researched and documented here so the integration can be executed
the moment both are available.

**What it is:** PersonaPlex is a full-duplex speech-to-speech model from NVIDIA — it
listens and speaks simultaneously, handles interruptions naturally, and accepts persona
control via a text prompt. Released January 2026, MIT code license, NVIDIA Open Model
license for weights. The text prompt persona control maps directly to SOUL.md — no
architectural changes needed on the Adam side.

**Why it's relevant:** The current voice layer (Edge TTS) is one-way — text in,
speech out, generic voice. PersonaPlex would replace that with a real-time
conversational interface where Adam listens while speaking, handles barge-ins, stays
in character, and responds in a consistent trained voice. The persona prompt is just
SOUL.md content passed at initialization.

**The two hard blockers today (March 2026):**
- **No hosted API.** PersonaPlex is weights-only — local deployment only. It is not
  available at `integrate.api.nvidia.com` or any other hosted endpoint.
- **No OpenClaw native support.** The OpenClaw integration is an open feature request,
  not a shipped feature. The plumbing doesn't exist yet.
- **Local deployment requires NVIDIA discrete GPU + CUDA.** Not viable on integrated
  graphics setups regardless of quantization.

**Integration path when both blockers are resolved:**
```
Voice message → OpenClaw
  → PersonaPlex API (persona from SOUL.md text prompt, voice output)
  → Kimi K2.5 API (tool use, memory, Vault — unchanged)
  → PersonaPlex API (speaks Kimi's response in Adam's voice)
  → Audio back to Telegram
```

**Watch for:**
- PersonaPlex appearing at `integrate.api.nvidia.com`
- Native PersonaPlex support merged into OpenClaw mainline
- Either of these makes this a same-day integration

---

## Longer Term 💡

Not scoped yet. Ideas worth tracking.

- **Web UI for Vault management** — browse and edit identity files, view neural graph
  connections, trigger reconcile runs manually
- **Multi-vault support** — separate Vaults for work vs. personal, shared Vault for
  team deployments
- **Confidence decay tuning** — expose reconcile parameters so operators can control
  how fast older facts fade vs. how strongly recent sessions reinforce
- **Cross-device sync** — Vault sync via git, so the same identity loads on multiple
  machines
- **Voice-first setup** — full install flow via Telegram voice messages only.
  No terminal required.
- **Automatic openclaw patch management** — detect openclaw version changes, re-apply
  known patches automatically, alert operator if manual review needed

---

## What Will Never Be In This Roadmap

- Cloud dependencies or hosted services — this framework runs locally, period
- Vendor lock-in to any specific model — model-agnostic is a hard constraint
- Anything that makes the Vault files non-human-readable

The architecture is: files you can read, a model that reads them, and infrastructure
you control. That's the foundation everything else is built on.

---

*Last updated: March 19, 2026*
