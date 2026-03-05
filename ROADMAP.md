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
- ✅ **Telegram interface** — full bidirectional conversation, voice via Edge TTS, heartbeat routing
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
  available at `integrate.api.nvidia.com` or any other hosted endpoint. For setups
  where Kimi K2.5 runs as a remote API call (no local discrete GPU), there is
  currently nothing to point a `baseUrl` at.
- **No OpenClaw native support.** The OpenClaw integration is an open feature request
  (#15392), not a shipped feature. The plumbing doesn't exist yet.
- **Local deployment requires NVIDIA discrete GPU + CUDA.** Not viable on integrated
  graphics setups regardless of quantization.

**Community quantization (for discrete GPU setups):**
A Q4_K GGUF version exists at `Codes4Fun/personaplex-7b-v1-q4_k-GGUF` on HuggingFace
— roughly half the VRAM of the full 7B model. An `--cpu-offload` flag exists but
real-time audio streaming on CPU alone produces unusable latency.

**Integration path when both blockers are resolved:**
The architecture for a remote-API setup is clean — no hardware changes required:

```
Voice message → OpenClaw
  → PersonaPlex API (persona from SOUL.md text prompt, voice output)
  → Kimi K2.5 API (tool use, memory, Vault — unchanged)
  → PersonaPlex API (speaks Kimi's response in Adam's voice)
  → Audio back to Telegram
```

For the openclaw.json config, the swap is surgical — replace the current Edge TTS
`provider` block with a PersonaPlex endpoint, same pattern as the existing NVIDIA
provider block. SENTINEL manages nothing new; PersonaPlex runs as a hosted service.

**Watch for:**
- PersonaPlex appearing at `integrate.api.nvidia.com` (NVIDIA's pattern with open
  models is to follow weights release with hosted API — Kimi K2.5 is the proof)
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

---

## Problem Two — Within-Session Coherence Degradation 🔬

The Adam Framework solved AI Amnesia: the identity and memory collapse that happens
*between* sessions. That's shipped, production-validated, and documented with receipts.

There is a second problem. It was the defining failure mode that created Layer 4.

**The problem:** As a session accumulates context, the model's reasoning consistency,
identity coherence, and decision quality degrade — quietly, before compaction triggers,
while the conversation is still nominally "working." The model doesn't announce this.
It just starts drifting. Priorities blur. Earlier decisions get quietly contradicted.
The persona established at boot begins to soften. By the time compaction fires, damage
is already done.

This is **within-session coherence degradation**. It is distinct from AI Amnesia
(between-session memory loss) and it is currently unsolved.

**What Layer 4 actually is:** The compaction flush is a *defensive* mitigation. When
context exhaustion is imminent, the AI writes what matters to the Vault before it's
lost. This recovers continuity *after* degradation. It does not prevent degradation
from happening.

---

### The Scratchpad Dropout Finding 🔬

This is a production observation, not a theory. It has been occurring consistently
across long sessions and was identified through direct operator use — not instrumented
monitoring.

**The setup:** The Adam Framework defines a mandatory cognitive loop — a ReAct
(Reason, Act, Verify) sequence — that the AI is required to execute in a scratchpad
block before any tool use, complex logic, or workspace change. This loop includes
synthesis, shadow simulation (think 3 steps ahead), identity check against SOUL.md,
and a structural integrity check before acting. It is defined as CRITICAL in AGENTS.md
and is loaded into every session via BOOT_CONTEXT injection.

**The observation:** In long sessions, Adam stops using the scratchpad. Not
occasionally — consistently, and at a predictable point as context depth increases.
The responses continue. The tools still fire. Everything looks like it's working.
But the internal cognitive scaffolding has quietly dropped off. Adam stops reasoning
before acting and starts just acting.

**Why this happens:** The scratchpad instruction lives in AGENTS.md, loaded near the
top of the context window at session start. As the session accumulates turns, that
instruction gets pushed progressively deeper into the context. The model's attention
weakens on it. It doesn't forget the instruction exists — it just stops weighting it
heavily enough to execute it. The behavior that defines the identity degrades silently
while the surface-level responses remain functional.

**Why this is significant:** Scratchpad dropout is a natural, binary, production-
validated behavioral signal for within-session coherence degradation.

Most proposed drift detection approaches are either:
- **Token-budget-only** — crude, correlative, doesn't tell you *what* degraded
- **External evaluation models** — expensive, adds latency, requires infrastructure

Scratchpad dropout is neither. It uses the system's own defined behavior as the
detector. When Adam is coherent, the scratchpad fires. When he's drifting, it stops.
The signal is already present in every session — it just hasn't been instrumented yet.

This is the coherence indicator that Layer 5 will be built on.

---

### Layer 5 — Coherence Monitor (Designed, Not Yet Built)

**What the next layer looks like:** A proactive coherence monitor — a system that
establishes a behavioral baseline from the Vault at session start, tracks scratchpad
usage and context depth mid-session, and re-injects identity-critical context before
drift becomes unrecoverable. Not reactive cleanup. Active maintenance.

```
Session start
  → SENTINEL compiles BOOT_CONTEXT (Layer 1, exists)
  → coherence_baseline.json written: scratchpad_expected, context_depth, session_time

Every 10 message turns
  → coherence_monitor.py checks two signals:
      SIGNAL 1 — context depth % (token budget consumed vs window size)
      SIGNAL 2 — scratchpad usage in last 10 turns (present or absent)
  → Writes to coherence_log.json with drift_score and action taken

Re-injection trigger (scratchpad absent + context depth > threshold)
  → Pull ReAct loop from AGENTS.md + current priorities from active-context.md
  → Inject as lightweight re-anchor (~200 tokens)
  → Log re-injection event with turn number, context depth, and score

Session end
  → coherence_log.json fed into nightly reconcile run (Layer 4, exists)
  → Drift patterns captured in CORE_MEMORY.md — compounds over time
```

The architecture follows the same philosophy as everything else in this framework:
- **Local and file-based** — `coherence_baseline.json` and `coherence_log.json`
  are human-readable. Open them and see exactly what the system saw and when it acted.
- **Model-agnostic** — coherence monitoring is an orchestration layer, not a
  retraining requirement. Works with any model running in OpenClaw.
- **Same pattern as existing tools** — `coherence_monitor.py` lives in `tools/`
  alongside `reconcile_memory.py`. SENTINEL manages it. Nothing new to learn.

**Current state:** Designed. Scratchpad dropout finding documented. Build not yet
started — this is the active research frontier of the Adam Framework.

**Why this matters beyond this repo:** Within-session coherence degradation affects
every long-context AI deployment. The reason most production AI systems cap session
length, force resets, or require human check-ins at intervals is precisely this
problem — it just isn't named clearly or addressed architecturally. The scratchpad
dropout finding gives it a name, a mechanism, and a measurable signal. The Adam
Framework is positioned to be the first local, file-based, model-agnostic system
to solve it — using the same approach that solved AI Amnesia: built in production,
validated by someone who needed it to work.

---

## What Will Never Be In This Roadmap

- Cloud dependencies or hosted services — this framework runs locally, period
- Vendor lock-in to any specific model — model-agnostic is a hard constraint
- Anything that makes the Vault files non-human-readable

The architecture is: files you can read, a model that reads them, and infrastructure
you control. That's the foundation everything else is built on.

---

*Last updated: March 2026*
