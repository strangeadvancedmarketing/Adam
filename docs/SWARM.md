# SWARM — Multi-Agent Coordination Without Direct Messaging

> How the Adam Framework coordinates multiple AI agents using shared memory
> instead of agent-to-agent communication.

---

## The Problem With Multi-Agent Systems

Most multi-agent architectures rely on direct messaging: Agent A sends a task to
Agent B, B processes it, B sends a result back to A. This requires:

- A message broker or orchestration layer
- Agents that know about each other
- Synchronous or async handoff protocols
- Error handling for agent failures mid-chain

This complexity scales badly. Add more agents, add more failure modes. The system
becomes brittle at the coordination layer.

The Adam Framework takes a different approach: **agents don't talk to each other.
They talk to the Vault.**

---

## The Shared Memory Model

Every agent in the swarm reads from and writes to the same Vault directory. The Vault
is the coordination layer. Agents are consumers and producers of Vault state — not
participants in a message-passing network.

```
┌─────────────────────────────────────────────────────────────┐
│                         THE VAULT                           │
│                                                             │
│  CORE_MEMORY.md    ← shared state all agents read          │
│  workspace/tasks/  ← task queue: files are tasks           │
│  workspace/output/ ← results: agents write here            │
│  workspace/memory/ ← daily logs: agents append here        │
└─────────────────────────────────────────────────────────────┘
        ▲           ▲           ▲           ▲
        │           │           │           │
   [ADAM]      [AGENT_1]   [AGENT_2]   [AGENT_N]
   orchestrator  specialist  specialist  specialist
```

**Coordination happens through file state, not message passing.**

---

## How Tasks Are Distributed

Tasks are files in `workspace/tasks/`. An agent claims a task by:

1. Reading the task file
2. Writing a `.lock` file with its agent ID
3. Processing the task
4. Writing the result to `workspace/output/`
5. Deleting the task file (and lock)

No message broker. No central scheduler. The filesystem is the queue.

```
workspace/tasks/
├── lead_research_doctor_paver_corp.md    ← unclaimed task
├── lead_research_doctor_paver_corp.lock  ← claimed by PATTERN_SEEKER
└── site_build_jl_artificial_grass.md    ← unclaimed task
```

The lock file prevents two agents from processing the same task simultaneously.
On Windows, this uses the same atomic write pattern as OpenClaw's session store —
write to temp, rename to lock. First rename wins.

---

## Agent Types in the Framework

### Adam (Orchestrator)
The primary agent running on OpenClaw. Reads completed results from `workspace/output/`,
updates `CORE_MEMORY.md` with findings, generates new tasks based on active project state.
Does not do specialist work directly — delegates via task files.

### PATTERN_SEEKER (Research Agent)
Monitors Reddit and other sources for signals matching defined patterns (e.g., South
Florida contractors without websites). Writes structured lead files to `workspace/tasks/`
for Adam to review and route to next steps. Runs on a separate process, reports back
through the Vault.

### Future Specialist Agents
Any process that can read/write files can participate in the swarm:
- **SITE_BUILDER** — takes a lead file, generates a demo GitHub Pages site
- **OUTREACH** — takes a qualified lead, drafts and queues an outreach message
- **MONITOR** — watches a target URL for changes, writes diff reports to output/

---

## The Zero-Direct-Messaging Constraint

Agents in this architecture **never communicate with each other directly.** This is
a hard constraint, not a preference. The reasons:

**Failure isolation.** If PATTERN_SEEKER crashes, Adam doesn't crash. If Adam is
restarting, PATTERN_SEEKER keeps running and writing to the task queue. Agents fail
independently. The Vault persists through all of it.

**Auditability.** Every task, every result, every piece of coordination is a file
you can read. There's no hidden message-passing state. If something went wrong, look
at the files.

**Asynchrony by default.** Agents run on their own schedules. PATTERN_SEEKER might
run every 6 hours. Adam might process its output queue once a day. The Vault bridges
the time gap. No synchronization primitives needed.

**Model-agnostic.** The orchestrator is Adam (Kimi K2.5 via OpenClaw). Specialist
agents can run different models, different runtimes, even different languages — as
long as they can read and write files in the expected format.

---

## Current Swarm State

As of March 2026, the swarm has one active specialist:

**PATTERN_SEEKER** — monitors 40+ subreddits for South Florida turf contractor leads.
Filters for contractors who: mention needing a website, ask for marketing advice, post
without a website link, or describe themselves as a new or growing operation.

Identified high-value prospects (no website, active on Reddit):
- Doctor Paver Corp
- J&L Artificial Grass
- Clean Turf Club
- MTP Turf

These were found by PATTERN_SEEKER and written to the task queue. Adam reviewed and
classified them. The contractor-prospector tool then generates demo sites for outreach.

---

## Wiring a New Agent

To add a specialist agent to the swarm:

**1. Define its task format** — what does a task file look like for this agent?
   Write a template to `vault-templates/tasks/YOUR_AGENT_task.template.md`

**2. Define its output format** — what does a result file look like?
   Write a template to `vault-templates/output/YOUR_AGENT_result.template.md`

**3. Build the agent** — any language, any model, any runtime. It needs to:
   - Poll `workspace/tasks/` for files matching its task format
   - Claim tasks via atomic lock file write
   - Process and write results to `workspace/output/`
   - Clean up task + lock files on completion

**4. Register it in AGENTS.md** (in your private Vault) — document what it does,
   what task formats it reads, what output formats it writes, and its schedule.

**5. Tell Adam about it** — update `CORE_MEMORY.md` with the new agent's capabilities
   so Adam knows what to delegate and what to expect back.

---

## Why This Scales

The swarm architecture has no theoretical limit on agents because there's no central
broker to bottleneck. Adding a new agent means: write a new task format, build a process
that reads and writes files. That's it.

The Vault becomes the single source of truth for all agent state. Adam reads it at
every session. The full picture is always available. No agent state is hidden in a
message queue somewhere — it's all in files you can inspect.

This is the same principle as the rest of the Adam Framework:

> **The state is in the files. The agents are just readers and writers.**
