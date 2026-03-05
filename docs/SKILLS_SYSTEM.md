# Skills System — Pluggable Capability Architecture

> How the Adam Framework extends AI behavior beyond conversation
> through a modular skill layer that lives in the Vault.

---

## What a Skill Is

A skill is a self-contained capability module that lives in `workspace/skills/`.
Each skill has its own directory with:

- **`SKILL.md`** — the manifest: purpose, tools, usage, commands, safety rules
- **Supporting scripts** — Python, PowerShell, JS, or any runtime
- **Local state files** — JSON, SQLite, or flat files the skill maintains

Skills are not plugins loaded by the gateway. They are **read by the AI** — the SKILL.md
manifest tells Adam what the skill does, what tools it exposes, and how to invoke it.
The AI then calls those tools when the task matches.

This means skills require zero gateway modification. You add a skill by adding a
directory and pointing Adam at the SKILL.md. That's the entire install.

---

## The Skills Directory

```
workspace/skills/
├── context-compiler/       <- AI-to-AI handoff with memory injection
│   ├── SKILL.md
│   └── context_compiler.py
├── contractor-prospector/  <- Find contractors without websites, build demo sites
│   ├── SKILL.md
│   ├── scripts/
│   └── templates/
├── email-intelligence/     <- Proactive email triage and alerting
│   ├── SKILL.md
│   └── known_entities.json
├── synthesis/              <- Latent pattern recognition across conversation
│   └── SKILL.md
└── quantum/                <- IBM quantum circuit experiments (research)
    └── SKILL.md
```

---

## Active Skills

### context-compiler
**What it does:** Compiles dense context briefs from the neural graph for external
AI handoffs. Formats memory as structured triples with confidence scores. Parses
structured learnings from the response back into the graph.

**The core problem it solves:** Every external AI starts blank. The context-compiler
eliminates the re-explanation tax by injecting a targeted memory brief before any
external call and capturing what was learned afterward.

**The handoff format:**
```
[HIPPOCAMPUS HANDOFF | Task: {task} | Tokens: ~{count} | Source: Adam]

IDENTITY: You are receiving context from a persistent AI system.
ACTIVE PROJECT: {project}: {one_line_status}
RELEVANT FACTS: {subject} {predicate} {object} [conf:{score}]
TASK: {exact_task}

RETURN PROTOCOL: After task, output:
[NEW LEARNINGS]
LEARNED: subject | predicate | object
[END LEARNINGS]
```

**Tools exposed:** `generate_context_brief`, `ingest_ai_response`

**Philosophy:** You own the memory layer. External AIs are commodity compute.
The bond accumulates in your graph, not scattered across AI silos.

---

### contractor-prospector
**What it does:** Finds contractors in target verticals (turf, landscaping, HVAC,
pressure washing) who have no website. Builds a demo site using a template, deploys
it to GitHub Pages, and prepares outreach.

**Full workflow:**
```
PROSPECT -> ENRICH -> BUILD SITE -> OUTREACH
```

**Target:** South Florida contractors without websites. Discovery via Firecrawl
search across Facebook, Yelp, and Google. Current focus: artificial turf vertical.

**Identified prospects (no website, active):**
Doctor Paver Corp, J&L Artificial Grass, Clean Turf Club, MTP Turf

**Outreach model:** Build the demo site first, then send the email.
$299 one-time or $49/month managed. 3-5 prospects per session max.

---

### email-intelligence
**What it does:** Transforms the inbox from a passive dump into a proactive signal
stream. Scans, categorizes, scores, and alerts on high-priority emails.

**The four intelligence layers:**
1. **Ingest** — IMAP scan of recent unread
2. **Categorize** — Urgent / Important / Noise / Relationship / Unknown
3. **Enrich** — Match against known entities, escalate priority accordingly
4. **Alert** — Telegram notification when score is 8+ and email unread over 2 hours

**Urgency scoring:** 9-10 = immediate action (legal/financial/deadline), 7-8 = today,
5-6 = 24 hours, 1-4 = digest or purge.

**Safety rules:** Never auto-send. Never delete. Escalate uncertainty. Log everything.

**The pattern this establishes:** Same intelligence layer applies to file system
monitoring, calendar deadlines, project health checks, and webhook alerting.
Master one signal stream, clone the pattern across the ecosystem.

---

### synthesis
**What it does:** Pattern recognition that runs as Step 0 of the reasoning loop
before the scratchpad opens. Identifies recurring structural patterns across scales
and surfaces the relevant pattern before responding.

**Activates on:** Cross-domain mentions, emotional weight, pattern language, complexity
threshold, meta-awareness questions. Silent for simple factual queries.

**Core patterns tracked:** Scattering/Overwhelm Loop, Alignment/Breakthrough Loop,
Recurrence/Teacher Pattern, Bridge/Threshold Moment, Resonance/Field Effect.

**Output:** 50-100 token pattern note in scratchpad before full response. Logged to
`workspace/pattern-log.md` for long-term frequency tracking.

---

## Writing a New Skill

A skill is a directory with a SKILL.md. Minimum viable manifest:

```markdown
# [Skill Name]

## Purpose
What problem this solves and why it exists.

## Tools
What commands or functions this skill exposes, inputs, outputs.

## Usage
How to invoke this skill. Real command examples.

## Safety Rules
What this skill must never do.

## Files
What state files this skill maintains and where.
```

Add the directory, tell Adam where the SKILL.md is, it is live. No gateway changes.
No config updates. No install process.

---

## The Design Philosophy

Skills are documentation-first because the AI is the runtime.

A traditional plugin system requires an API, a loader, a sandbox — infrastructure
that can break. The Adam Framework's skill system requires a Markdown file the AI
can read.

The tradeoff: skills can only do what the AI can do with tools already available —
file read/write, MCP calls, shell commands via Desktop Commander. You cannot write
a skill that adds a new native capability to the gateway.

What you can do is give the AI a clear, structured description of a capability that
already exists. The AI will use it correctly because the SKILL.md tells it exactly how.

The Vault is the plugin registry. SKILL.md is the plugin manifest. The AI is the
plugin loader. No infrastructure required.
