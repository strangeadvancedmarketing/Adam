# Human Setup Guide — Adam Framework

> **Starting line:** You have OpenClaw installed and a model talking to you.
> That's all this assumes. This guide gives your AI a persistent soul, memory, and identity.

---

## What You're Actually Getting

Right now your AI is amnesiac. Every session starts blank. It doesn't know your name, your projects, or what you talked about yesterday.

This framework changes that. By the end of this guide:

- Your AI knows who it is and who you are — before you say a single word
- Every session builds on the last. No re-explaining. No repeating yourself.
- The neural graph grows over time — your AI starts making connections you didn't teach it
- Your entire conversation history from Claude, ChatGPT, or both gets loaded in as a foundation — **Session 000**

**Time required:** ~60 minutes on first setup. Permanent payoff.

---

## What Gets Built

| Layer | What It Is | Why It Matters |
|-------|-----------|----------------|
| **Vault** | A folder of plain Markdown files | Your AI's long-term memory lives here |
| **Identity Files** | SOUL.md + CORE_MEMORY.md | The AI reads these at every boot |
| **SENTINEL** | A watchdog PowerShell script | Starts your AI automatically, keeps it alive, runs coherence checks |
| **Neural Graph** | A local associative memory database | Builds connections between concepts over time |
| **Session 000** | Your full chat history ingested as facts | Your AI wakes up already knowing your history |
| **Sleep Cycle** | Nightly Gemini-powered consolidation | Daily logs merged into core memory while you sleep |
| **Coherence Monitor** | Layer 5 — scratchpad dropout detection | Catches within-session drift every 5 min, auto re-anchors |

---

## Prerequisites

Before starting, confirm you have:

- [ ] **OpenClaw** installed and a model responding when you chat
- [ ] **Python 3.10+** — `python --version` in PowerShell
- [ ] **mcporter** — `npm install -g mcporter`
- [ ] **Git** (optional but recommended) — for cloning and version tracking
- [ ] **A Gemini API key** (free) — for the sleep cycle. Get one at [aistudio.google.com](https://aistudio.google.com/app/apikey)

**What is mcporter?** It's the MCP server router that wires external tools into OpenClaw — neural memory, search, Notion, etc. Install it once, configure it, and OpenClaw gains those capabilities.

---

## Phase 1 — Give Your AI an Identity (30 min)

### Step 1: Create Your Vault

Your Vault is the directory where your AI's memory lives. Plain Markdown files. Readable, editable, git-trackable.

```powershell
mkdir "C:\MyAIVault"
mkdir "C:\MyAIVault\workspace"
mkdir "C:\MyAIVault\workspace\memory"
mkdir "C:\MyAIVault\imports"
```

**Tip:** Short path, no spaces. You'll reference it in several places.

---

### Step 2: Fill In Your Identity Files

These are the most important files in the entire framework. Your AI reads them at every single boot. The more specific and honest you are, the more coherent your AI will be.

Copy the templates into your Vault:

```powershell
copy vault-templates\SOUL.template.md "C:\MyAIVault\SOUL.md"
copy vault-templates\CORE_MEMORY.template.md "C:\MyAIVault\CORE_MEMORY.md"
copy vault-templates\BOOT_SEQUENCE.md "C:\MyAIVault\workspace\BOOT_SEQUENCE.md"
copy vault-templates\active-context.template.md "C:\MyAIVault\workspace\active-context.md"
copy vault-templates\coherence_baseline.template.json "C:\MyAIVault\workspace\coherence_baseline.json"
copy vault-templates\coherence_log.template.json "C:\MyAIVault\workspace\coherence_log.json"
```

Now open **SOUL.md** in any text editor. Fill in every `{{PLACEHOLDER}}`:

- `{{YOUR_AI_NAME}}` — what you want to call your AI
- `{{YOUR_NAME}}` — your name
- `{{YOUR_ROLE}}` — what kind of work you do
- `{{YOUR_AI_PERSONALITY}}` — how you want it to communicate
- `{{YOUR_BUSINESS_CONTEXT}}` — your current projects, business, goals

Then open **CORE_MEMORY.md** and do the same. This file is your AI's living knowledge base — it gets updated automatically over time by the sleep cycle. Seed it with the real state of your work right now.

**Take your time with these files.** A 30-minute investment here compounds every session.

---

### Step 3: Configure openclaw.json

Open your existing openclaw.json at `$env:USERPROFILE\.openclaw\openclaw.json`.

You're adding the Vault paths to your existing working config — **do not overwrite your whole file.** Find or add these sections:

**extraPaths** — tells OpenClaw which files to index:
```json
"extraPaths": [
  "C:\\MyAIVault\\CORE_MEMORY.md",
  "C:\\MyAIVault\\workspace\\memory",
  "C:\\MyAIVault\\workspace\\BOOT_CONTEXT.md"
]
```

**vault path** — wherever your config references a vault or memory path, update it to `C:\\MyAIVault` (double backslashes in JSON).

If your openclaw.json has a `memoryFlush` or compaction prompt, update any hardcoded paths in it to match your Vault.

**Not sure what's in your openclaw.json?** See `engine/openclaw.template.json` for a reference of the full structure with all fields explained. Use it as a guide, not a replacement.

---

### Step 4: Set Up and Test SENTINEL

SENTINEL is the watchdog that starts your AI on login, writes the authoritative date, compiles boot context from your identity files, and keeps the gateway alive if it crashes.

Copy the template to your OpenClaw directory:

```powershell
copy engine\SENTINEL.template.ps1 "$env:USERPROFILE\.openclaw\SENTINEL.ps1"
```

Open `SENTINEL.ps1` and update the variables at the top:

```powershell
$VAULT_PATH  = "C:\MyAIVault"   # ← your actual Vault path
$PYTHON_EXE  = "python"         # override if python isn't in your PATH
```

Run it manually to test:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.openclaw\SENTINEL.ps1"
```

You should see:
```
[2026-03-03 10:00:01] Sentinel rising. Clearing stale processes...
[2026-03-03 10:00:03] Date injected: 2026-03-03
[2026-03-03 10:00:03] Compiling BOOT_CONTEXT.md...
[2026-03-03 10:00:03] BOOT_CONTEXT.md compiled successfully.
[2026-03-03 10:00:04] Gateway started - PID 12345
[2026-03-03 10:00:04] SENTINEL ACTIVE — Watchdog loop starting.
```

**First win:** Open `http://localhost:18789` and say hello. Your AI should greet you by name and know its role. That's the identity layer working.

---

### Step 5: Register SENTINEL for Auto-Start

So it runs automatically every time you log in:

```powershell
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$env:USERPROFILE\.openclaw\SENTINEL.ps1`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask `
    -TaskName "AISentinel" `
    -Action $action `
    -Trigger $trigger `
    -RunLevel Highest `
    -Force
```

After this: every login, SENTINEL starts silently. Your AI is always ready. Check `$env:USERPROFILE\.openclaw\sentinel.log` to confirm it ran.

---

## Phase 2 — Give Your AI Memory (15 min)

### Step 6: Install Neural Memory

```powershell
pip install neural_memory
```

Configure mcporter to route it into OpenClaw. Find your mcporter config location:

```powershell
mcporter config path
```

Copy the template there:

```powershell
copy engine\mcporter.template.json (mcporter config path)
```

Open the mcporter config and ensure the `neural-memory` block is present. Remove any blocks for services you don't have keys for yet — you can add them later.

Test it:

```powershell
mcporter call "neural-memory.nmem_stats()"
```

Expected: `{"neurons": 0, "synapses": 0}` — zero is correct on first run.

**Second win:** Your AI now has a neural graph. It starts empty but builds connections between every concept, person, and project you work on. Week 1 it's basic. Month 1 it's making associations you didn't teach it.

---

## Phase 3 — Session 000: Seed Your History (15 min + background ingest)

This is the step most people skip — and it's the difference between an AI that vaguely knows you and one that genuinely knows your history from day one.

You're going to export your conversation history from Claude and/or ChatGPT, extract the meaningful facts from it, review them, and feed them into your neural graph.

---

### Step 7: Export Your Conversation History

**From Claude (claude.ai):**
1. Go to claude.ai → Settings → Privacy → Export Data
2. You'll get an email with a download link — click it
3. Download the zip file — it contains `conversations.json`

**From ChatGPT (chatgpt.com):**
1. Go to chatgpt.com → Settings → Data Controls → Export Data
2. Download the zip — it also contains `conversations.json`

You can run the importer on one or both exports.

---

### Step 8: Extract Facts (Step 1 of 2)

Run the legacy importer on your export file. This reads your conversations and pulls out meaningful facts — decisions, tools, relationships, projects — into a reviewable JSON file.

```powershell
python tools\legacy_importer.py `
    --source "C:\path\to\your\export.zip" `
    --vault-path "C:\MyAIVault" `
    --user-name "YourFirstName"
```

**Options:**
- `--source` — path to your export zip or extracted conversations.json
- `--vault-path` — your Vault directory
- `--user-name` — your name as it appears in your conversations (helps pattern matching)
- `--format claude` or `--format chatgpt` — override auto-detection if needed

The extractor auto-detects format. It runs in seconds to a few minutes depending on how many conversations you have.

**Output:**
- `C:\MyAIVault\imports\extracted_triples.json` — the facts file (review this)
- `C:\MyAIVault\imports\extraction_report.txt` — human-readable summary

**Open `extraction_report.txt` first.** It shows you how many facts were found and a sample of 20. Open `extracted_triples.json` if you want to review or edit the raw facts before committing them to the graph.

You can delete any entries that look wrong. The file is plain JSON — each fact is a 3-element array: `["subject", "predicate", "object"]`.

---

### Step 9: Ingest Into Neural Graph (Step 2 of 2)

Once you've reviewed the extracted facts:

```powershell
.\tools\ingest_triples.ps1 -VaultPath "C:\MyAIVault"
```

**Options:**
- `-DryRun` — shows what would be ingested without actually running (test first)
- `-StartAt 150` — resume from a specific fact number if the run was interrupted

**Do a dry run first:**
```powershell
.\tools\ingest_triples.ps1 -VaultPath "C:\MyAIVault" -DryRun
```

Then run for real. Estimated time: ~56 minutes for 740 facts. **You can use your AI normally while this runs in the background.** Don't close the PowerShell window until it finishes.

When it completes you'll see:
```
Session 000 complete. Your AI already knows you.
```

**Third win:** Your AI's neural graph now contains the accumulated knowledge from your entire conversation history. Every decision, tool, project, and relationship you've discussed with any AI — now lives in its memory.

---

## Phase 4 — Make It Self-Sustaining

### Step 10: Copy Tools to Your Vault

SENTINEL looks for the sleep cycle and coherence monitor scripts inside your Vault at runtime. You need to copy them there:

```powershell
Copy-Item -Recurse "tools" "C:\MyAIVault\tools"
```

Verify:
```powershell
Test-Path "C:\MyAIVault\tools\reconcile_memory.py"
Test-Path "C:\MyAIVault\tools\coherence_monitor.py"
```

Both should return `True`. If either returns `False`, SENTINEL will silently skip that component on every boot — no error, just a log line saying "not found - skipping."

### Step 11: Add Your Gemini API Key

The sleep cycle uses Gemini to merge daily logs into CORE_MEMORY.md. Add your key to openclaw.json:

Open `$env:USERPROFILE\.openclaw\openclaw.json` and find (or add) the `env` block:
```json
"env": {
  "GEMINI_API_KEY": "your-key-here"
}
```

Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

**What happens automatically after this:**

**Every time your system starts:**
- SENTINEL checks if the sleep cycle has run in the last 6 hours
- If not, it runs `reconcile_memory.py` before launching the gateway
- Daily session logs get merged into CORE_MEMORY.md via Gemini
- New facts get incrementally added to the neural graph
- After the gateway is healthy, the vector index gets updated

**What feeds the sleep cycle:**
Daily session logs landing in `C:\MyAIVault\workspace\memory\` — written by OpenClaw automatically if you configure `memoryFlush` in openclaw.json. See `engine/openclaw.template.json` for the exact config block.

---

## Optional: Telegram Access

This lets you message your AI from your phone. Not required, but highly recommended once everything is working.

1. Open Telegram → message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token you receive
4. In `openclaw.json`, add to the `channels` block:

```json
"channels": {
  "telegram": {
    "enabled": true,
    "botToken": "YOUR_BOT_TOKEN_HERE"
  }
}
```

5. Restart SENTINEL
6. Find your bot in Telegram and message it — same AI, from your phone

---

## The Experience Arc

**Day 1:**
Your AI knows your name, your projects, and its own role. Sessions start with context. You stop re-explaining yourself.

**Week 1:**
The neural graph has real connections. Your AI starts referencing things from previous sessions without being prompted. It's building an associative map of your work.

**Month 1:**
Daily logs have genuine history. The sleep cycle has merged weeks of sessions into CORE_MEMORY.md. The AI has accumulated real decisions, real project state, real context. The compounding has started.

**This is what 353 sessions of real use looks like:** [docs/PROOF.md](docs/PROOF.md)

---

## Troubleshooting

**"Gateway won't start"**
Check `$env:USERPROFILE\.openclaw\sentinel.log`. Usually a bad JSON in openclaw.json (unclosed bracket, trailing comma). Validate it at [jsonlint.com](https://jsonlint.com).

**"AI doesn't know who it is"**
BOOT_CONTEXT.md wasn't compiled. Check that `C:\MyAIVault\CORE_MEMORY.md` exists and `$VAULT_PATH` in SENTINEL.ps1 is correct. Restart SENTINEL.

**"nmem_stats() hangs or errors"**
mcporter can't find the neural-memory server. Confirm: `mcporter config path` shows a valid file, the file has the neural-memory block, and `python -m neural_memory.mcp_server` runs without error.

**"Execution of scripts is disabled"**
Run in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**"extracted_triples.json is empty or has very few facts"**
Normal if your conversations were mostly short exchanges. Try `--max-per-conv 50` for more aggressive extraction. Also make sure `--user-name` matches how your name appears in your chats.

**"Ingest is stuck / failed at fact #X"**
Run with `-StartAt X` to resume from where it stopped. Check that mcporter is running and `nmem_stats()` returns a response.

**"Sleep cycle not running"**
Check sentinel.log for "Sleep cycle skipped" messages. Most common cause: GEMINI_API_KEY not in openclaw.json env block, or the `_reconcile_state.json` thinks it ran recently. Delete the state file to force a run: `del "C:\MyAIVault\workspace\memory\_reconcile_state.json"`.
