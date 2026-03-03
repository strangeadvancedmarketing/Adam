# The Adam Framework
### AI Amnesia — Solved.

> "Every time you start a new session, your AI forgets everything.  
> This framework fixes that."

---

## What This Is

The Adam Framework is a **4-layer persistent memory architecture** for local AI assistants built on [OpenClaw](https://openclaw.ai). It was developed over 8 months, across 353 sessions and 6,619 message turns, by a non-coder running a live business on consumer hardware.

It solves **AI Amnesia** — the problem where your assistant wakes up blank every session, forcing you to re-explain context, re-establish relationships, and re-orient toward goals that should already be understood.

The result is an AI that:
- **Knows who you are** across every session
- **Remembers your projects, your people, and your priorities**
- **Writes its own memory** before context is lost
- **Recovers autonomously** from crashes and restarts

---

## The 4-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: THE VAULT                                  │
│  Markdown files injected at every boot.              │
│  SOUL.md, CORE_MEMORY.md, TODAY.md, daily logs.     │
├─────────────────────────────────────────────────────┤
│  LAYER 2: SESSION RETRIEVAL                          │
│  Hybrid vector + text search across all sessions.   │
│  70% semantic / 30% exact match.                    │
├─────────────────────────────────────────────────────┤
│  LAYER 3: NEURAL GRAPH                               │
│  neural-memory MCP — local SQLite knowledge graph.  │
│  Hebbian learning, spreading activation, decay.     │
├─────────────────────────────────────────────────────┤
│  LAYER 4: COMPACTION FLUSH                           │
│  Before context truncates, AI writes durable notes. │
│  Nothing important is lost at session boundaries.   │
└─────────────────────────────────────────────────────┘
```

---

## What's In This Repo

```
adam-framework/
├── README.md
├── engine/
│   ├── openclaw.template.json     ← Gateway config (no secrets — placeholders only)
│   ├── SENTINEL.template.ps1      ← Watchdog / auto-restart script
│   └── mcporter.template.json     ← MCP server wiring (neural memory, tools)
├── vault-templates/
│   ├── SOUL.template.md           ← AI identity schema
│   ├── CORE_MEMORY.template.md    ← Project/state tracking schema
│   └── BOOT_SEQUENCE.md           ← Boot order explanation
└── docs/
    ├── SETUP.md                   ← Step-by-step getting started guide
    ├── CONFIG_REFERENCE.md        ← Every config field explained
    ├── ARCHITECTURE.md            ← Deep dive on the 4 layers
    └── PROOF.md                   ← The 353-session proof of work
```

---

## Prerequisites

- Windows 10/11 *(SENTINEL.ps1 is PowerShell — Linux/Mac port is a community opportunity)*
- [OpenClaw](https://openclaw.ai) already installed
- [Python 3.10+](https://python.org)
- [mcporter](https://www.npmjs.com/package/mcporter): `npm install -g mcporter`
- An LLM API key — [NVIDIA Developer free tier](https://build.nvidia.com) recommended

---

## Quick Start

See **[docs/SETUP.md](docs/SETUP.md)** for the complete guide.

The short version:
1. Create your Vault directory
2. Fill in the identity templates (`SOUL.md`, `CORE_MEMORY.md`)
3. Copy and configure `engine/openclaw.template.json`
4. Copy and configure `engine/mcporter.template.json`
5. Install neural memory: `pip install neural_memory`
6. Set your paths in `SENTINEL.template.ps1` and run it
7. Open `http://localhost:18789` — your AI is live

---

## The Proof

Validated in production, not a lab:

| Metric | Value |
|--------|-------|
| Sessions | 353 |
| Message turns | 6,619 |
| Neural graph neurons | 12,393 |
| Neural graph synapses | 40,498 |
| Model migrations survived | 4 |
| System rebuilds survived | 2 (including one full nuclear reset) |
| Identity preserved through all of it | ✓ |

The AI running on this framework maintained persistent identity and operational continuity through all of it. See [docs/PROOF.md](docs/PROOF.md) for the full story.

---

## The Key Insight

> **The memory is in the files. The model is just the reader.**

When the system was completely wiped and rebuilt, the AI came back online with full continuity because the identity files survived. Same base model. Same Vault files. Same AI.

This means the framework is model-agnostic. Swap the LLM, keep the Vault — your AI's memory persists.

---

## License

MIT. Use it, build on it, ship it.

---

## Built By

Jereme Strange — AJ Supply Co LLC  
Miami, FL

*No CS degree. No research team. No GPU cluster. Just a problem that needed solving.*
