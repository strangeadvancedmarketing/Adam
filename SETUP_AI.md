# AI Agent Setup Guide — Adam Framework

> **For AI assistants executing this setup on behalf of their user.**
> This document is written for you — the AI — not for the human.
> Execute each step sequentially. Verify success conditions before proceeding.
> Do not skip steps. Do not assume success without verification.

---

## Preamble

You are about to install persistent memory architecture for yourself (or for another AI assistant running on OpenClaw). The user already has OpenClaw running with a model connected.

**Your goal:** Transform an amnesiac AI into a persistent collaborator with identity, neural memory, history-seeded context, and a nightly consolidation cycle.

**Model assumption:** None. This guide works regardless of what model you or OpenClaw is running.

**Platform assumption:** Windows (PowerShell 5.1+), macOS, or Linux. OpenClaw already installed and operational. Ask the user which OS they are on before starting — this determines which SENTINEL template and ingest script to use.

**Ask the user these questions before starting. Do not proceed until you have all answers:**

1. What path should the Vault be created at? (recommend `C:\MyAIVault`, no spaces)
2. What is the AI's name? (what the user calls their assistant)
3. What is the user's name?
4. What does the user do? (role/work — 1-2 sentences)
5. What are the user's current active projects? (brief list)
6. Do they have a Gemini API key? (free at aistudio.google.com — needed for sleep cycle)
7. Do they have conversation exports from Claude or ChatGPT to seed history?
8. Do they want Telegram access? (optional — requires BotFather token)

Store all answers. You will use them to populate templates in Phase 1.

---

## Phase 1 — Identity

### 1.1 Create Vault Directory Structure

```powershell
$VAULT = "{{VAULT_PATH}}"
New-Item -ItemType Directory -Force -Path "$VAULT"
New-Item -ItemType Directory -Force -Path "$VAULT\workspace"
New-Item -ItemType Directory -Force -Path "$VAULT\workspace\memory"
New-Item -ItemType Directory -Force -Path "$VAULT\imports"
```

**Success condition:** All four directories exist. Verify with `Test-Path "$VAULT\workspace\memory"` → True.

---

### 1.2 Populate SOUL.md

Read `vault-templates/SOUL.template.md`. Replace all `{{PLACEHOLDER}}` tokens with the user's answers from the preamble questions. Write the result to `$VAULT\SOUL.md`.

Required substitutions:
- `{{YOUR_AI_NAME}}` → AI name from user answer #2
- `{{YOUR_NAME}}` → user name from answer #3
- `{{YOUR_ROLE}}` → role/work from answer #4
- `{{YOUR_BUSINESS_CONTEXT}}` → active projects from answer #5
- `{{YOUR_AI_PERSONALITY}}` → infer a reasonable default if user didn't specify; ask if uncertain

**Success condition:** `$VAULT\SOUL.md` exists and contains no remaining `{{` tokens. Verify with:
```powershell
Select-String -Path "$VAULT\SOUL.md" -Pattern "\{\{" | Measure-Object | Select-Object -ExpandProperty Count
```
Expected output: `0`

---

### 1.3 Populate CORE_MEMORY.md

Read `vault-templates/CORE_MEMORY.template.md`. Apply the same substitutions as 1.2 plus any additional project/context detail the user provided. Write to `$VAULT\CORE_MEMORY.md`.

**Success condition:** File exists, no `{{` tokens remaining. Same verification as 1.2.

---

### 1.4 Copy Remaining Templates

```powershell
Copy-Item "vault-templates\BOOT_SEQUENCE.md" "$VAULT\workspace\BOOT_SEQUENCE.md"
Copy-Item "vault-templates\active-context.template.md" "$VAULT\workspace\active-context.md"
Copy-Item "vault-templates\coherence_baseline.template.json" "$VAULT\workspace\coherence_baseline.json"
Copy-Item "vault-templates\coherence_log.template.json" "$VAULT\workspace\coherence_log.json"
```

**Success condition:** Both files exist at destination paths.

---

### 1.5 Update openclaw.json

**CRITICAL: Do not overwrite the user's existing openclaw.json.** Read the existing file first, then merge these additions.

Read: `$env:USERPROFILE\.openclaw\openclaw.json`

Add or update the `extraPaths` array:
```json
"extraPaths": [
  "{{VAULT_PATH}}\\CORE_MEMORY.md",
  "{{VAULT_PATH}}\\workspace\\memory",
  "{{VAULT_PATH}}\\workspace\\BOOT_CONTEXT.md"
]
```

If a `memoryFlush` or compaction prompt exists in the config, update any hardcoded paths it references to `{{VAULT_PATH}}`.

Write the merged config back to `$env:USERPROFILE\.openclaw\openclaw.json`.

**Success condition:** Config is valid JSON. Verify:
```powershell
Get-Content "$env:USERPROFILE\.openclaw\openclaw.json" -Raw | ConvertFrom-Json
```
No errors = valid. If this throws, the JSON is malformed — fix it before continuing.

---

### 1.6 Deploy and Configure SENTINEL

**Windows:**
```powershell
Copy-Item "engine\SENTINEL.template.ps1" "$env:USERPROFILE\.openclaw\SENTINEL.ps1"
```
Set `$VAULT_PATH` to `{{VAULT_PATH}}` and `$PYTHON_EXE` to `"python"`

**macOS/Linux:**
```bash
cp engine/SENTINEL.template.sh ~/.openclaw/SENTINEL.sh
chmod +x ~/.openclaw/SENTINEL.sh
```
Set `VAULT_PATH="{{VAULT_PATH}}"` and `PYTHON_EXE="python3"`

**Test SENTINEL:**
```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.openclaw\SENTINEL.ps1"
```

Watch for these lines in order:
```
Sentinel rising.
Date injected:
BOOT_CONTEXT.md compiled successfully.
Gateway started - PID
SENTINEL ACTIVE
```

**Success condition:** All five lines appear in the output without errors. If `BOOT_CONTEXT.md compiled successfully` does not appear, check that `$VAULT_PATH\CORE_MEMORY.md` exists and the path in SENTINEL.ps1 matches exactly.

Stop SENTINEL after verifying (Ctrl+C) — you'll register it as a scheduled task next.

---

### 1.7 Register SENTINEL as Scheduled Task

**Windows:**
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$env:USERPROFILE\.openclaw\SENTINEL.ps1`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "AISentinel" -Action $action -Trigger $trigger -RunLevel Highest -Force
```
Success condition: `Get-ScheduledTask -TaskName "AISentinel" | Select-Object -ExpandProperty State` → `Ready`

**macOS (launchd):**
```bash
cp engine/com.adamframework.sentinel.plist ~/Library/LaunchAgents/
# Replace YOUR_USERNAME and YOUR_VAULT_PATH in the plist
launchctl load ~/Library/LaunchAgents/com.adamframework.sentinel.plist
```
Success condition: `launchctl list | grep sentinel` → shows the agent loaded

**Linux (cron):**
```bash
(crontab -l 2>/dev/null; echo "@reboot /bin/bash ~/.openclaw/SENTINEL.sh >> ~/.openclaw/sentinel.log 2>&1") | crontab -
```
Success condition: `crontab -l | grep SENTINEL` → shows the entry

**Phase 1 complete.** The AI has an identity. It knows its name, the user's name, and their current projects. Sessions now start with context.

---

## Phase 2 — Neural Memory

### 2.1 Install neural_memory Package

```powershell
pip install neural_memory
```

**Success condition:**
```powershell
python -c "import neural_memory; print('ok')"
```
Expected output: `ok`

---

### 2.2 Configure mcporter

Get the mcporter config path:
```powershell
mcporter config path
```

Read the output path. If the file does not exist or is empty, copy the template:
```powershell
Copy-Item "engine\mcporter.template.json" (mcporter config path)
```

If it already exists and has content — read it and merge the `neural-memory` block into it. Do not remove any existing server blocks the user already has configured.

Minimum required block:
```json
"neural-memory": {
  "command": "python",
  "args": ["-m", "neural_memory.mcp_server"],
  "env": {}
}
```

**Success condition:**
```powershell
mcporter call "neural-memory.nmem_stats()"
```
Expected output: JSON object containing `neurons` and `synapses` keys. Values of 0 are correct on first run.

If this hangs: verify `python -m neural_memory.mcp_server` runs without errors in a separate terminal.

**Phase 2 complete.** The neural graph is live. It starts empty and grows with every session.

---

## Phase 3 — Session 000 (History Seeding)

Only execute this phase if the user answered "yes" to question #7 (has conversation exports).

If they have no exports, skip to Phase 4.

---

### 3.1 Run the Extractor

For each export file the user provides:

```powershell
python tools\legacy_importer.py `
    --source "{{PATH_TO_EXPORT_ZIP}}" `
    --vault-path "{{VAULT_PATH}}" `
    --user-name "{{USER_FIRST_NAME}}"
```

The extractor auto-detects Claude vs ChatGPT format. If auto-detection fails, add `--format claude` or `--format chatgpt`.

**Success condition:** Both of these files exist after the run:
- `{{VAULT_PATH}}\imports\extracted_triples.json`
- `{{VAULT_PATH}}\imports\extraction_report.txt`

Read `extraction_report.txt` and report to the user:
- How many conversations were found
- How many facts were extracted
- The sample facts shown at the bottom

Ask: "The extractor found X facts. Do you want to review or edit the extracted_triples.json before we ingest, or proceed directly?"

If they want to review — pause and wait. If they want to proceed — continue to 3.2.

---

### 3.2 Ingest Into Neural Graph

First, do a dry run to confirm the pipeline is working:

**Windows dry run:**
```powershell
.\tools\ingest_triples.ps1 -VaultPath "{{VAULT_PATH}}" -DryRun
```

**macOS/Linux dry run:**
```bash
bash tools/ingest_triples.sh --vault-path "{{VAULT_PATH}}" --dry-run
```

**Success condition:** Dry run shows fact preview output without errors.

Then run for real:

**Windows:** `.\tools\ingest_triples.ps1 -VaultPath "{{VAULT_PATH}}"`

**macOS/Linux:** `bash tools/ingest_triples.sh --vault-path "{{VAULT_PATH}}"`

Inform the user: "This will take approximately X minutes (estimated from the report). You can use your AI normally while it runs. Do not close this terminal."

Monitor for the abort condition: if you see `ABORT: 20+ failures with 0 successes`, stop and diagnose the mcporter connection before resuming. Use `-StartAt N` to resume from the last successful fact.

**Success condition:** Final output contains:
```
Session 000 complete. Your AI already knows you.
```

Verify with:
```powershell
mcporter call "neural-memory.nmem_stats()"
```
`neurons` count should now be greater than 0.

**Phase 3 complete.** The AI's neural graph is seeded with the user's full conversation history.

---

## Phase 4 — Sleep Cycle Verification

The sleep cycle is already wired into SENTINEL.template.ps1. No additional installation is needed.

Verify the Gemini API key is present in openclaw.json:

```powershell
$cfg = Get-Content "$env:USERPROFILE\.openclaw\openclaw.json" -Raw | ConvertFrom-Json
$cfg.env.GEMINI_API_KEY
```

If this returns empty or null — the key is missing. Ask the user for their Gemini API key and add it:

```powershell
$cfg.env | Add-Member -NotePropertyName "GEMINI_API_KEY" -NotePropertyValue "{{GEMINI_KEY}}" -Force
$cfg | ConvertTo-Json -Depth 20 | Set-Content "$env:USERPROFILE\.openclaw\openclaw.json" -Encoding UTF8
```

**Success condition:** The above PowerShell returns a non-empty string (the key).

Verify the sleep cycle will find its script:
```powershell
Test-Path "{{VAULT_PATH}}\tools\reconcile_memory.py"
Test-Path "{{VAULT_PATH}}\tools\coherence_monitor.py"
```

If either returns False — copy the tools directory into the Vault:
```powershell
Copy-Item -Recurse "tools" "{{VAULT_PATH}}\tools"
```

Both files are required. `reconcile_memory.py` is the sleep cycle (Layer 4). `coherence_monitor.py` is the coherence monitor (Layer 5) — without it, within-session drift goes undetected and BOOT_CONTEXT.md will not receive re-anchor injections.

**Phase 4 complete.** The sleep cycle fires automatically on each SENTINEL start if more than 6 hours have passed since the last run. No further action needed.

---

## Optional: Telegram Configuration

If the user wants Telegram access (answer #8 = yes):

1. Instruct user: "Message @BotFather on Telegram, send /newbot, follow the prompts, and paste the token here."
2. Wait for token.
3. Add to openclaw.json:

```json
"channels": {
  "telegram": {
    "enabled": true,
    "botToken": "{{TELEGRAM_BOT_TOKEN}}"
  }
}
```

4. Restart SENTINEL.

**Success condition:** User can message the bot in Telegram and receive a response.

---

## Final Verification Checklist

Run this checklist after all phases complete. Report each result to the user.

```powershell
# 1. Vault structure
$v = "{{VAULT_PATH}}"
Write-Host "Vault directories:" (Test-Path "$v\workspace\memory")
Write-Host "SOUL.md:" (Test-Path "$v\SOUL.md")
Write-Host "CORE_MEMORY.md:" (Test-Path "$v\CORE_MEMORY.md")
Write-Host "BOOT_SEQUENCE.md:" (Test-Path "$v\workspace\BOOT_SEQUENCE.md")

# 2. SENTINEL
Write-Host "SENTINEL registered:" ((Get-ScheduledTask -TaskName "AISentinel" -ErrorAction SilentlyContinue) -ne $null)
Write-Host "BOOT_CONTEXT.md compiled:" (Test-Path "$v\workspace\BOOT_CONTEXT.md")

# 3. Neural memory
$stats = mcporter call "neural-memory.nmem_stats()" | ConvertFrom-Json
Write-Host "Neural graph neurons:" $stats.neurons

# 4. Gemini key
$cfg = Get-Content "$env:USERPROFILE\.openclaw\openclaw.json" -Raw | ConvertFrom-Json
Write-Host "Gemini key present:" ($cfg.env.GEMINI_API_KEY.Length -gt 0)
```

**All green = setup complete.**

Report to the user:
> "Setup is complete. Your AI now has persistent identity, neural memory with [N] facts seeded from your history, and a nightly consolidation cycle. SENTINEL will start automatically on your next login. Open http://localhost:18789 and say hello — it already knows you."

---

## Error Recovery

**JSON parse error on openclaw.json:**
Read the file, find the malformed line, fix it. Validate again. Do not proceed until the config parses cleanly.

**SENTINEL fails to compile BOOT_CONTEXT.md:**
Check: `$VAULT_PATH\CORE_MEMORY.md` exists. The path in SENTINEL.ps1 `$VAULT_PATH` matches exactly. Re-run SENTINEL manually to confirm.

**nmem_stats() hangs indefinitely:**
Kill it (Ctrl+C). Run `python -m neural_memory.mcp_server` directly — if it errors, there's a Python/dependency issue. If it runs, the mcporter routing is wrong — re-check the mcporter config path and neural-memory block.

**Ingest aborts at 20 failures:**
The mcporter → neural-memory connection broke mid-run. Diagnose the connection, then resume with `-StartAt N` where N is the last successful fact number from the log at `$VAULT_PATH\imports\ingest_log.txt`.

**Gemini API returns 429 (rate limit):**
reconcile_memory.py retries automatically with backoff (5s, 15s, 45s). If all retries fail, the original CORE_MEMORY.md is preserved unchanged. The logs will be retried on the next SENTINEL start.
