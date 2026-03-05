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

- ✅ **4-layer memory architecture** — Vault injection, session search, neural graph, nightly reconciliation
- ✅ **SENTINEL watchdog** — boot sequence, date injection, BOOT_CONTEXT compilation, auto-restart, sleep cycle
- ✅ **Neural graph integration** — 12,393 neurons / 40,532 synapses, live and growing
- ✅ **Legacy importer** — extract facts from Claude and ChatGPT export zips, seed neural graph before Session 000
- ✅ **Nightly reconcile** — Gemini merges daily logs into CORE_MEMORY.md, incremental neural ingest, metrics snapshot
- ✅ **Skills system** — documentation-first plugin architecture, four active skills in production
- ✅ **Telegram interface** — full bidirectional conversation, voice via Kokoro TTS, heartbeat routing
- ✅ **Email intelligence** — proactive inbox triage, urgency scoring, Telegram alerts
- ✅ **Contractor prospector** — lead discovery, demo site generation, GitHub Pages deploy, outreach
- ✅ **Context compiler** — AI-to-AI handoff with memory injection and structured return parsing
- ✅ **Nuclear reset validated** — system wiped and rebuilt, identity survived via Vault files

---

## Near Term 🔄 📋

Work in active progress or immediately next.

### Swarm pilot — PATTERN_SEEKER live fire
- 🔄 PATTERN_SEEKER agent monitoring 40+ subreddits for South Florida turf contractor leads
- 📋 Full swarm loop: PATTERN_SEEKER → task queue → contractor-prospector → outreach
- 📋 Swarm coordination documented in `docs/SWARM.md`, wiring to be finalized

### Neural metrics visualizer
- 📋 `showcase/neural-growth.html` — chart that reads `workspace/neural_metrics.json`
  and plots neuron/synapse growth over time. Makes the "live growing system" story
  visible to anyone who visits the repo.

### Windows Task Scheduler setup guide
- 📋 Step-by-step SENTINEL registration with screenshots. Biggest friction point
  in the current install flow. Eliminates the last manual step.

### `reconcile_memory.py` test coverage
- 📋 pytest suite covering state management, backup logic, LLM validation, and
  the neural diff ingest. Makes the core tool safer to iterate on.

---

## Community Opportunities 💡

High-value contributions that need someone to pick them up.

### Linux / macOS port of SENTINEL
`SENTINEL.template.ps1` is PowerShell-only. A bash equivalent covering the same
boot sequence — date injection, sleep cycle, BOOT_CONTEXT compilation, gateway
launch, watchdog loop — would open this framework to the majority of developers.
**This is the single highest-value contribution the project needs.**

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

---

## Voice Layer Upgrade — NVIDIA PersonaPlex 💡

Worth tracking closely. Not ready to integrate yet, but the trajectory is clear.

**What it is:** PersonaPlex is a full-duplex speech-to-speech model from NVIDIA — it
listens and speaks simultaneously, handles interruptions naturally, and accepts persona
control via a text prompt. That text prompt maps directly to SOUL.md. Released January
2026, MIT code license, NVIDIA Open Model license for weights.

**Why it's relevant:** The current voice layer (Kokoro TTS) is one-way — text in,
speech out. PersonaPlex would replace that with a real-time conversational voice
interface where Adam listens while speaking, handles barge-ins, and maintains persona
throughout. The persona-via-text-prompt architecture is a direct fit for how SOUL.md
already works.

**Current state:**
- Full model (7B): ~14-16GB VRAM — too heavy to run alongside Kimi K2.5 on most setups
- Community Q4_K GGUF quantization exists at `Codes4Fun/personaplex-7b-v1-q4_k-GGUF`
  on HuggingFace — cuts VRAM requirement roughly in half (~6-7GB)
- Official `--cpu-offload` flag exists for GPU-constrained setups
- Open feature request in OpenClaw repo (#15392) for native PersonaPlex integration
- Key limitation: PersonaPlex handles voice only, not tool use — still requires a
  separate LLM (Kimi K2.5 or similar) for the intelligence layer

**Integration path when ready:**
PersonaPlex runs its own server at `localhost:8998`. The architecture would be:
Telegram/mic input → PersonaPlex (voice layer, persona from SOUL.md) → Kimi K2.5
(tool use, memory, reasoning) → PersonaPlex (spoken response). SENTINEL would manage
both processes.

**Watch for:** Official OpenClaw PersonaPlex integration, further community
quantizations, and NVIDIA's promised production-focused architecture optimized for
lower VRAM usage. When a Q4_K or smaller runs cleanly alongside the main model,
this becomes a straightforward SENTINEL addition.

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

---

## What Will Never Be In This Roadmap

- Cloud dependencies or hosted services — this framework runs locally, period
- Vendor lock-in to any specific model — model-agnostic is a hard constraint
- Anything that makes the Vault files non-human-readable

The architecture is: files you can read, a model that reads them, and infrastructure
you control. That's the foundation everything else is built on.

---

*Last updated: March 2026*
