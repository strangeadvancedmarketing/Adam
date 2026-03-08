---
name: adam-framework
description: 5-layer persistent memory and coherence architecture for OpenClaw agents. Solves AI amnesia and within-session drift. Built and validated over 353 sessions on a live business. No CS degree required.
tags: [memory, persistence, identity, coherence, vault, neural-graph, local-first]
---

# Adam Framework

**AI Amnesia — Solved. Within-Session Coherence Degradation — Solved.**

The Adam Framework is a 5-layer persistent memory architecture for OpenClaw agents, developed over 8 months across 353 sessions on a live business by a non-coder running consumer hardware.

OpenClaw just got acquired by OpenAI. Your memory layer shouldn't be.

## What It Solves

- **AI Amnesia** — your agent wakes up blank every session, forcing you to re-explain context, projects, and goals that should already be known
- **Within-Session Drift** — as a session accumulates context, the model's reasoning consistency quietly degrades before compaction triggers

## The 5 Layers

| Layer | Component | What It Does |
|-------|-----------|--------------|
| 1 | Vault injection via SENTINEL | Identity files loaded at every boot. Agent wakes up knowing who it is. |
| 2 | memory-core plugin | Live memory search mid-session via memory_search / memory_get tools |
| 3 | Neural graph (nmem_context) | Associative recall — 12,393 neurons, 40,532 synapses. Concepts link to concepts. |
| 4 | Nightly reconciliation | Gemini merges daily logs into CORE_MEMORY.md while you sleep. Nothing lost. |
| 5 | Coherence monitor | Scratchpad dropout detector — fires re-anchor before drift causes damage. 33 tests passing. |

## The Key Insight

> **The memory is in the files. The model is just the reader.**

When the system was completely wiped and rebuilt from scratch, the agent came back online with full continuity — because the identity files survived. Swap the LLM, keep the Vault. Memory persists.

## Setup

Two paths — pick one:

**Path 1 — You do it yourself (30–60 min)**
Read [SETUP_HUMAN.md](https://github.com/strangeadvancedmarketing/Adam/blob/master/SETUP_HUMAN.md). Plain English, no technical background assumed.

**Path 2 — Let your agent handle it**
Paste [SETUP_AI.md](https://github.com/strangeadvancedmarketing/Adam/blob/master/SETUP_AI.md) into your OpenClaw chat. It asks 8 questions and does the install itself.

## Prerequisites

- OpenClaw running with any model
- Python 3.10+
- `npm install -g mcporter`
- NVIDIA Developer free tier API key (Kimi K2.5, 131K context, free)
- Gemini API key (free) for nightly reconciliation

## Links

- **Repo:** https://github.com/strangeadvancedmarketing/Adam
- **Live proof (353 sessions):** https://strangeadvancedmarketing.github.io/Adam/showcase/ai-amnesia-solved.html
- **Full setup guide:** https://github.com/strangeadvancedmarketing/Adam/blob/master/SETUP_HUMAN.md
