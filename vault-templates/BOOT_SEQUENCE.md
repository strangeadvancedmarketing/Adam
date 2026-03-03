# Boot Sequence — Why Order Matters

> This document explains the boot sequence that makes the Adam Framework work.
> Every step exists for a specific reason discovered through production experience.

---

## The Sequence

```
SENTINEL runs before every session:

Step 0 → Write TODAY.md (authoritative date)
Step 1 → Compile BOOT_CONTEXT.md from identity files
Step 2 → Launch OpenClaw Gateway
Step 3 → AI reads TODAY.md, CORE_MEMORY.md, daily log
Step 4 → AI calls nmem_context (neural graph recall)
Step 5 → AI is fully loaded. Session begins.
```

---

## Why Each Step Exists

### Step 0: Date Injection (TODAY.md)
**The problem it solves:** LLMs hallucinate dates from training data.

If you ask your AI what today's date is without telling it, it will guess based on its training cutoff — and it will be wrong. In production, this caused the AI to create memory logs with wrong dates, corrupting the daily log structure.

The fix is dead simple: SENTINEL writes a file containing the real date, and the AI is instructed to read it before doing anything dated. Completely reliable.

**What it looks like:**
```markdown
# Authoritative Date

Today is **2026-03-03** (Tuesday, March 03, 2026)

This file is written by SENTINEL at every gateway start.
It is the ONLY authoritative date source. Never guess. Always read this file first.
```

---

### Step 1: Boot Context Compilation (BOOT_CONTEXT.md)
**The problem it solves:** The AI's identity files are in the Vault, but it can't read them automatically without tool calls — and tool calls at boot are unreliable.

SENTINEL reads CORE_MEMORY.md and active-context.md *before* the gateway starts, compiles them into a single file (BOOT_CONTEXT.md), and OpenClaw injects that file as part of the memory search context automatically on session start.

This means the AI knows who it is, what projects are active, and what happened last session *before it says a single word* — without needing to call any tools.

**Why this matters:** Tool-call-dependent boots fail when MCP servers are slow, auth tokens expire, or the AI skips steps. Hard-compiled context is deterministic. It never fails.

---

### Step 2: Gateway Launch
Standard OpenClaw startup. Nothing clever here — just launch it after the prep steps.

---

### Step 3: AI Reads Vault Files
The AI's SOUL.md startup sequence tells it to read:
1. TODAY.md — get the date
2. CORE_MEMORY.md — project state and identity (already in BOOT_CONTEXT but re-read for verification)
3. memory/YYYY-MM-DD.md — today's log

This is Layer 1 of the memory architecture: structured, deterministic identity injection.

---

### Step 4: Neural Graph Recall (nmem_context)
**The problem it solves:** Structured files give you current state. The neural graph gives you *context* — the associative web of what's related to what.

`nmem_context` traverses the knowledge graph and surfaces memories relevant to the current moment based on spreading activation. This is how the AI remembers that the project you're working on today has a history from three weeks ago that matters.

This is Layer 3 of the memory architecture. It runs silently — no output, just internal context loading.

---

## The Compaction Flush (Layer 4)

This step happens *during* sessions, not at boot — but it's the most important step for long-term persistence.

When the session context nears its token limit, OpenClaw triggers the `memoryFlush` prompt:

```
"Write any lasting notes to your Vault memory file. Update CORE_MEMORY.md if 
project state has changed. Reply with NO_REPLY if nothing to store."
```

The AI writes durable notes to the daily log and updates CORE_MEMORY.md *before* the context is truncated. Nothing important is lost at session boundaries.

This is the core solve for AI amnesia. The AI writes its own memory continuously. The next session picks up exactly where the last one left off.

---

## What Happens Without Each Layer

| Without Layer | Symptom |
|---|---|
| No Vault files | AI wakes up blank every session |
| No date injection | AI uses wrong dates, corrupts memory logs |
| No BOOT_CONTEXT compilation | AI needs tool calls to load identity — unreliable |
| No neural graph | AI has facts but no associative context |
| No compaction flush | Context truncates, important state is lost |

---

## Session Boundary Behavior

A "session boundary" is when the context window fills up and OpenClaw starts a new session. Without the compaction flush, this is catastrophic — everything in the current session is lost.

With the compaction flush, it's a non-event. The AI writes what matters before truncation. The next session reads it back from the Vault. From the user's perspective, the conversation just continues.

This is the difference between an AI with amnesia and an AI with persistent memory.
