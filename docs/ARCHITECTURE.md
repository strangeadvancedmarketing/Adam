# Architecture — The 4-Layer Memory System

> A technical explanation of how the Adam Framework solves AI amnesia.

---

## The Problem

Every AI assistant has the same fundamental limitation: when a session ends, it forgets everything. The next session starts completely blank — no memory of your projects, your priorities, your people, or what you decided last week.

This is **AI Amnesia**, and it makes AI assistants fundamentally limited as long-term collaborators.

The fixes most people try:
- **Copy-paste context** at the start of every session → Tedious, incomplete, doesn't scale
- **Use the AI's built-in memory** → Shallow, unreliable, often wrong
- **Start over** every session → Defeats the purpose

The Adam Framework solves this at the architecture level with 4 complementary layers.

---

## Layer 1: The Vault (Structured Identity Files)

**What it is:** A directory of Markdown files that define who your AI is and what's currently happening.

**Core files:**
- `SOUL.md` — personality, operating principles, communication style
- `CORE_MEMORY.md` — active projects, key relationships, system state
- `TODAY.md` — the real date (written fresh by SENTINEL each boot)
- `workspace/memory/YYYY-MM-DD.md` — daily logs written by the AI
- `workspace/BOOT_CONTEXT.md` — compiled by SENTINEL, injected automatically

**How it works:** SENTINEL compiles CORE_MEMORY.md + active-context.md into BOOT_CONTEXT.md before each session. OpenClaw injects this file as part of its memory search context. The AI is instructed to read TODAY.md and the daily log as its first actions.

**Why Markdown?** Human-readable, AI-native, git-trackable, Obsidian-compatible. Every file is auditable and editable by the operator.

**What it solves:** The AI always knows who it is, what projects are active, and what happened recently — before it says a single word.

---

## Layer 2: Session Retrieval (Hybrid Search)

**What it is:** OpenClaw's built-in session memory with hybrid vector + text search.

**Configuration:**
```json
"query": {
  "hybrid": {
    "enabled": true,
    "vectorWeight": 0.7,
    "textWeight": 0.3,
    "candidateMultiplier": 4
  }
}
```

**How it works:** OpenClaw indexes all session content and the Vault files. When the AI needs context, it runs a hybrid search — 70% semantic vector similarity plus 30% exact text match — to surface the most relevant prior content.

**What it solves:** Within-session and cross-session recall of specific facts, decisions, and conversations. "What did we decide about X?" gets answered from actual session history.

---

## Layer 3: Neural Graph (Associative Memory)

**What it is:** The [neural-memory MCP](https://github.com/neural-memory/neural-memory) — a local SQLite knowledge graph with biologically-inspired memory mechanics.

**Key mechanics:**
- **Spreading activation** — related concepts activate each other through graph traversal
- **Hebbian learning** — connections strengthen when co-activated (use it or lose it)
- **Temporal decay** — unused connections weaken over time
- **Contradiction detection** — conflicting facts are flagged, not silently overwritten

**How it works:**
- New facts are stored as triples: `(subject, predicate, object)`
- `nmem_context` runs at session start, traverses the graph, surfaces contextually relevant memories
- `nmem_remember` stores new facts during sessions
- `nmem_recall` does targeted queries

**What it solves:** The difference between knowing a fact and understanding its context. The neural graph gives the AI the associative web — "this project is related to that person is related to this constraint" — that structured files alone can't provide.

**At scale (production numbers):**
- 12,393 neurons
- 40,498 synapses
- 353 sessions of accumulated knowledge

---

## Layer 4: Reconciliation (The Compaction Flush)

**What it is:** A trigger that fires when the session context nears its token limit, instructing the AI to write durable notes before truncation.

**Configuration in openclaw.json:**
```json
"memoryFlush": {
  "enabled": true,
  "softThresholdTokens": 4000,
  "prompt": "Write any lasting notes to YOUR_VAULT/memory/YYYY-MM-DD.md. Update CORE_MEMORY.md if project state has changed. Reply with NO_REPLY if nothing to store.",
  "systemPrompt": "You are YOUR_AI_NAME. Session nearing compaction. Store durable memories now."
}
```

**How it works:** When the session context is within 4,000 tokens of the limit, OpenClaw pauses and sends the memoryFlush prompt. The AI writes its notes to the daily log and updates CORE_MEMORY.md. Then the session continues or truncates — either way, nothing important was lost.

**What it solves:** This is the core solve for AI amnesia. Session boundaries become non-events. The AI continuously writes its own persistent memory. The next session picks up exactly where the last one left off.

---

## How the Layers Work Together

```
SESSION START
     │
     ▼
SENTINEL writes TODAY.md + compiles BOOT_CONTEXT.md
     │
     ▼
Gateway starts → OpenClaw injects BOOT_CONTEXT.md
     │
     ▼
AI reads TODAY.md + daily log (Layer 1)
     │
     ▼
AI calls nmem_context → neural graph surfaces relevant memories (Layer 3)
     │
     ▼
AI is fully loaded. Session begins.
     │
     │  [During session]
     ▼
OpenClaw hybrid search surfaces relevant prior context as needed (Layer 2)
     │
     ▼
Context approaches token limit → memoryFlush triggers (Layer 4)
     │
     ▼
AI writes lasting notes to Vault → truncation happens safely
     │
     ▼
NEXT SESSION → Layers 1-3 reload everything
```

---

## What Makes This Different From Built-in AI Memory

| Feature | Built-in AI Memory | Adam Framework |
|---|---|---|
| Reliability | Inconsistent | Deterministic |
| Auditability | Black box | Every file readable |
| Control | Model-dependent | Fully operator-controlled |
| Depth | Shallow summaries | Full structured state |
| Associative recall | None | Neural graph spreading activation |
| Compaction handling | Memory lost | Flush writes before truncation |
| Cross-session persistence | Hit or miss | Guaranteed via Vault |
| Cost | Vendor-dependent | Runs locally, free |
