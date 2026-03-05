# Architecture — The 5-Layer Memory and Coherence System

> A technical explanation of how the Adam Framework solves AI amnesia and within-session coherence degradation.

---

## The Problem

Every AI assistant has two fundamental limitations.

**AI Amnesia:** When a session ends, it forgets everything. The next session starts completely blank — no memory of your projects, your priorities, your people, or what you decided last week.

**Within-Session Coherence Degradation:** As a session accumulates context, the model's reasoning consistency and identity coherence quietly degrade — before compaction triggers, while the conversation is still nominally "working." The model doesn't announce this. It just starts drifting. Priorities blur. Earlier decisions get quietly contradicted. The scratchpad reasoning loop stops firing. By the time compaction hits, damage is already done.

The fixes most people try for AI Amnesia:
- **Copy-paste context** at the start of every session → Tedious, incomplete, doesn't scale
- **Use the AI's built-in memory** → Shallow, unreliable, often wrong
- **Start over** every session → Defeats the purpose

The Adam Framework solves both problems at the architecture level with 5 complementary layers.

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
- 40,532 synapses
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

## Layer 5: Coherence Monitor (Active Drift Detection)

**What it is:** A SENTINEL-managed monitoring script that runs every 5 minutes during active sessions, detecting within-session coherence degradation before it becomes unrecoverable.

**The signal — scratchpad dropout:** The Adam Framework defines a mandatory ReAct (Reason-Act-Verify) cognitive loop that the AI executes in a scratchpad block before any complex action. When the AI is coherent, it uses the scratchpad consistently. When it drifts — as context depth increases and the scratchpad instruction gets pushed deep in the context window — it stops. This is a binary, production-validated behavioral signal.

**How it works:**
- Reads the live OpenClaw session JSONL line-by-line (the real format)
- Measures real token depth from the API `usage.input` field (not character estimation — base64 images in tool results inflate char counts by 10x)
- Checks scratchpad tag presence across the last 10 assistant turns
- Computes a drift score 0.0–1.0; score ≥0.6 triggers re-anchor
- Writes re-anchor content to `reanchor_pending.json`
- SENTINEL detects the file and injects the content into `BOOT_CONTEXT.md` — same injection path already proven at boot

**Re-anchor content:** ~200 tokens pulled from `AGENTS.md` (the ReAct loop definition) plus current priorities from `active-context.md`. Lightweight. Targeted. Enough to pull the model back to its operational patterns.

**Exit codes:** 0 = coherent, 1 = drift detected + re-anchor written, 2 = error

**Files:**
- `tools/coherence_monitor.py` — the monitor
- `tools/test_coherence_monitor.py` — 30-test suite, validated against live session data before first production run
- `vault-templates/coherence_baseline.template.json` — session baseline schema
- `vault-templates/coherence_log.template.json` — event log schema (session-scoped, resets daily)

**What it solves:** Within-session coherence degradation. The AI stays grounded through long sessions. The scratchpad keeps firing. Drift is caught and corrected before damage is done.

---

## How All 5 Layers Work Together

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
     │  [During session — every turn]
     ▼
OpenClaw hybrid search surfaces relevant prior context as needed (Layer 2)
     │
     │  [During session — every 5 minutes via SENTINEL]
     ▼
coherence_monitor.py checks scratchpad usage + real token depth (Layer 5)
     │
     ├─ Coherent → log exit 0, continue
     │
     └─ Drift detected → write reanchor_pending.json
                             │
                             ▼
                       SENTINEL injects re-anchor into BOOT_CONTEXT.md
                       AI course-corrects on next context load
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
| Within-session coherence | Unmonitored, degrades silently | Layer 5 active monitoring + re-anchor |
| Cost | Vendor-dependent | Runs locally, free |
