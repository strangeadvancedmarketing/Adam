# Setup Guide — Adam Framework

> **This guide assumes you already have OpenClaw installed.**
> If you don't: `npm install -g openclaw` — then come back here.

---

## What You're Building

By the end of this guide you'll have:
- A **Vault** — a folder of Markdown files that IS your AI's memory
- A **SENTINEL** watchdog that starts your AI automatically and keeps it alive
- A **neural memory graph** that builds associative knowledge over time
- An AI that knows who you are, what you're working on, and what happened last session — every single session

This takes about 30 minutes on a clean setup.

---

## Prerequisites

- [ ] Windows 10 or 11 *(Linux/Mac: community port welcome — SENTINEL is the only Windows-specific piece)*
- [ ] OpenClaw already installed and running
- [ ] [Python 3.10+](https://python.org) — needed for the neural memory MCP
- [ ] [mcporter](https://www.npmjs.com/package/mcporter) installed

```powershell
npm install -g mcporter
```

**What is mcporter?** It's the MCP server router that wires external tools (neural memory, Firecrawl, Notion, etc.) into OpenClaw. Install it once, configure it in `mcporter.template.json`, and OpenClaw gains tool access.

**Optional but recommended:**
- [Obsidian](https://obsidian.md) — opens your Vault as a visual knowledge base
- A Telegram bot token — lets you message your AI from your phone

---

## Step 1: Clone This Repo

```powershell
git clone https://github.com/YOUR_HANDLE/adam-framework.git
cd adam-framework
```

Or download and unzip if you don't use git.

---

## Step 2: Create Your Vault

Your Vault is the directory where your AI's memory lives. All files are plain Markdown — readable, editable, git-trackable.

```powershell
mkdir "C:\MyAIVault"
mkdir "C:\MyAIVault\workspace"
mkdir "C:\MyAIVault\workspace\memory"
```

**Tip:** Short path, no spaces. You'll reference this path in several config files.

---

## Step 3: Get an LLM API Key

The framework was built and tested on **NVIDIA Developer free tier** — it gives you access to Kimi K2.5 (131K context) and Llama 3.3 70B at no cost.

1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Create a free account
3. Navigate to API Keys → Generate Key
4. Copy it — you'll use it in Step 5

**Using a different provider?** Any OpenAI-compatible API works (OpenAI, Anthropic via OpenRouter, Groq, etc.). Update the `baseUrl` and `apiKey` in `openclaw.json` accordingly.

---

## Step 4: Set Up Your Identity Files

These are the most important files in the entire framework. The AI reads them at every boot. The more honest and specific you are, the more coherent your AI will be.

```powershell
copy vault-templates\SOUL.template.md "C:\MyAIVault\workspace\SOUL.md"
copy vault-templates\CORE_MEMORY.template.md "C:\MyAIVault\CORE_MEMORY.md"
copy vault-templates\BOOT_SEQUENCE.md "C:\MyAIVault\workspace\BOOT_SEQUENCE.md"
```

Now open both `SOUL.md` and `CORE_MEMORY.md` and fill them in:

**In SOUL.md:** Replace every `[YOUR_*]` placeholder with real descriptions of your AI's personality, role, and operating style.

**In CORE_MEMORY.md:** Replace every `[YOUR_*]` placeholder with your real name, projects, and any context your AI needs to know about your work.

Also create a blank active-context file:

```powershell
echo "# Active Context`n`nNo active task." > "C:\MyAIVault\workspace\active-context.md"
```

---

## Step 5: Configure openclaw.json

Copy the template to your OpenClaw config directory:

```powershell
copy engine\openclaw.template.json "$env:USERPROFILE\.openclaw\openclaw.json"
```

Open `$env:USERPROFILE\.openclaw\openclaw.json` and make these replacements:

| Find | Replace with |
|------|-------------|
| `YOUR_LLM_API_KEY` | Your NVIDIA (or other) API key |
| `YOUR_PROVIDER_NAME` | `nvidia` (or your provider name) |
| `YOUR_PROVIDER/YOUR_MODEL_ID` | `nvidia/moonshotai/kimi-k2.5` (or your model) |
| `YOUR_AI_NAME` | Whatever you want to call your AI |
| `YOUR_VAULT_PATH` | `C:\\MyAIVault` (double backslashes in JSON) |
| `GENERATE_A_RANDOM_32_CHAR_HEX_STRING` | Run this and paste the output: |

```powershell
python -c "import secrets; print(secrets.token_hex(16))"
```

**Important:** The `extraPaths` section tells OpenClaw which files to index. Make sure all three paths point to your actual Vault:

```json
"extraPaths": [
  "C:\\MyAIVault\\CORE_MEMORY.md",
  "C:\\MyAIVault\\workspace\\memory",
  "C:\\MyAIVault\\workspace\\BOOT_CONTEXT.md"
]
```

Also update the `memoryFlush` prompt to use your real Vault path and AI name.

**Not using Telegram?** Delete the entire `channels` block from the config.

**Not using TTS?** Delete the entire `messages.tts` block.

---

## Step 6: Configure mcporter.json

mcporter lives in its own config location. Find it:

```powershell
mcporter config path
```

Copy the template there:

```powershell
copy engine\mcporter.template.json (mcporter config path)
```

Edit the file — at minimum, you need the `neural-memory` block. Remove any server blocks for tools you don't have API keys for. You can add them later.

**Minimum working config** (just neural-memory, no other services):

```json
{
  "servers": {
    "neural-memory": {
      "command": "python",
      "args": ["-m", "neural_memory.mcp_server"],
      "env": {}
    }
  }
}
```

---

## Step 7: Install Neural Memory

```powershell
pip install neural_memory
```

Test it:

```powershell
mcporter call "neural-memory.nmem_stats()"
```

Expected output: a JSON object with `neurons: 0, synapses: 0`. Zero is correct on first run — the graph builds as you use the system.

If this command hangs or errors, check that mcporter is installed (`mcporter --version`) and that your mcporter.json has the neural-memory block from Step 6.

---

## Step 8: Configure and Test SENTINEL

Copy the watchdog script:

```powershell
copy engine\SENTINEL.template.ps1 "$env:USERPROFILE\.openclaw\SENTINEL.ps1"
```

Open `SENTINEL.ps1` and update the two variables at the top:

```powershell
$VAULT_PATH  = "C:\MyAIVault"    # ← your actual Vault path
$USE_KOKORO  = $false            # leave false unless you install Kokoro TTS
```

**Run it manually to test:**

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.openclaw\SENTINEL.ps1"
```

You should see output like:
```
[2026-03-03 10:00:01] Sentinel rising. Clearing stale processes...
[2026-03-03 10:00:03] Date injected: 2026-03-03
[2026-03-03 10:00:03] Compiling BOOT_CONTEXT.md...
[2026-03-03 10:00:03] BOOT_CONTEXT.md compiled successfully.
[2026-03-03 10:00:03] Launching OpenClaw Gateway...
[2026-03-03 10:00:04] Gateway started - PID 12345
[2026-03-03 10:00:04] SENTINEL ACTIVE — Watchdog loop starting.
```

If you see this, SENTINEL is working. Leave this window open — SENTINEL runs in the foreground.

**Common issue:** "Set-Content: Could not find part of the path"
→ Your Vault path is wrong, or you skipped creating the workspace/memory folders in Step 2.

---

## Step 9: Register SENTINEL for Auto-Start

So your AI starts automatically every time you log into Windows:

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

After this, SENTINEL starts hidden on every login. Check `$env:USERPROFILE\.openclaw\sentinel.log` to verify it ran.

---

## Step 10: Talk to Your AI

Open a browser: `http://localhost:18789`

Your AI will greet you. It should already know its name and role from SOUL.md.

**If using Telegram:**
1. Create a bot: message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`
2. Copy the token into `openclaw.json` → `channels.telegram.botToken`
3. Restart SENTINEL
4. Message your bot — you'll be talking to your AI from your phone

---

## What Happens Next (The Framework Learning)

The first few sessions, your AI knows what you put in the identity files. That's it.

Over time, as you use it:
- The **neural graph** builds up connections between concepts, people, and projects
- The **daily memory logs** accumulate in `workspace/memory/`
- The **CORE_MEMORY.md** gets updated by the AI itself when project state changes
- The **compaction flush** writes durable notes before any context truncation

After a few weeks of real use, the AI has genuine persistent context. The memory compounds. This is the solve for AI amnesia — not magic, just consistent architecture.

---

## Troubleshooting

**Gateway won't start:**
- Check `sentinel.log` in `$env:USERPROFILE\.openclaw\`
- Open `openclaw.json` — look for unclosed brackets or quotes (JSON must be valid)
- Run `openclaw doctor` in PowerShell

**BOOT_CONTEXT.md not being created:**
- SENTINEL couldn't find `CORE_MEMORY.md` at the path you set
- Verify `$VAULT_PATH` in SENTINEL.ps1 matches where you actually put the file
- Check the sentinel.log for the exact error message

**AI doesn't know who it is:**
- Check that BOOT_CONTEXT.md exists in `YOUR_VAULT\workspace\`
- Verify `extraPaths` in openclaw.json points to the right Vault location
- Restart SENTINEL so it recompiles BOOT_CONTEXT.md

**Neural memory command hangs:**
- mcporter may not be finding the neural-memory server
- Check mcporter.json is in the right location: `mcporter config path`
- Ensure Python is in your PATH: `python --version`

**"Execution of scripts is disabled" error:**
- Run in PowerShell as Administrator:
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Date is wrong in memory logs:**
- SENTINEL writes TODAY.md — check it was created in `YOUR_VAULT\workspace\`
- The AI must read TODAY.md before creating any dated files (this is in SOUL.md startup sequence)
