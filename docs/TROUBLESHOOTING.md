# Troubleshooting

> Fast diagnostic guide for the most common failure modes.
> For full root cause analysis and production incident writeups, see `docs/LESSONS_LEARNED.md`.

---

## Quick Diagnostic Checklist

Run these before anything else when something is wrong:

```powershell
# 1. Is the gateway alive?
Invoke-WebRequest "http://127.0.0.1:18789/health" -UseBasicParsing

# 2. Is the config valid?
Get-Content "$env:USERPROFILE\.openclaw\openclaw.json" -Raw | ConvertFrom-Json | Out-Null

# 3. Any config errors in today's log?
Get-Content "C:\tmp\openclaw\openclaw-$(Get-Date -Format 'yyyy-MM-dd').log" |
  Select-String 'ERROR|invalid config|Unrecognized key'

# 4. Is SENTINEL running?
Get-ScheduledTask -TaskName "ClawdSentinel" | Select-Object State, LastRunTime

# 5. mcporter daemon alive?
mcporter daemon status
```

---

## `memory_search` returns "Tool not found"

**Symptoms:** Adam calls `memory_search` or `memory_get` and gets "Tool not found".
The gateway log shows `memory-core | loaded`. `openclaw memory status` reports the index healthy.

**Root cause:** Two separate things must be true. Either one missing = tools don't register.

**Fix 1 — Check `agents.defaults.memorySearch.enabled`:**
```powershell
$oc = Get-Content "$env:USERPROFILE\.openclaw\openclaw.json" -Raw | ConvertFrom-Json
$oc.agents.defaults.memorySearch.enabled
# Must return: True
```
If it returns nothing or False, add `"enabled": true` to the `agents.defaults.memorySearch` block.

**Fix 2 — Verify the `api.config` patch is in place:**
```powershell
Select-String -Path "$env:APPDATA\npm\node_modules\openclaw\extensions\memory-core\index.ts" -Pattern "api\.config"
```
If no output → the patch was overwritten by an openclaw update. Re-apply it:
- Open `extensions/memory-core/index.ts`
- Find both occurrences of `config: ctx.config`
- Change both to `config: api.config`
- Kill the gateway (SENTINEL restarts it)
- Start a fresh session and retest

A backup of the patched file is at:
`C:\Users\ajsup\.openclaw\EMERGENCY_SNAPSHOT\extensions\memory-core-index.ts`

> **Why this happens:** The memory-core plugin uses `emptyPluginConfigSchema()` — meaning `ctx.config` inside the tool factory is intentionally empty. `api.config` is the full gateway config. See LESSONS_LEARNED.md [2026-03-19] for the full writeup.

---

## Gateway crash loop (starts and dies every 30 seconds)

**Symptoms:** SENTINEL log shows `Gateway started - PID XXXXX` then `WARNING: Gateway process died. Restarting...` repeating every 30 seconds. Adam never responds.

**Root cause:** Almost always a bad `openclaw.json`.

**Fix:**
```powershell
# Capture the actual error
$dir = "$env:USERPROFILE\.openclaw"
cmd /c "`"$dir\gateway.cmd`" > C:\tmp\gw_out.txt 2> C:\tmp\gw_err.txt"
Get-Content C:\tmp\gw_err.txt
```
Look for `Config invalid` or `Unrecognized key`. Fix the flagged key, then restart SENTINEL.

**Common bad keys:**
- Anything under `plugins.allow` that isn't an installed plugin name
- `channels.telegram.streamMode` (deprecated — use `streaming`)
- Any key under `skills` other than top-level `{}`
- Custom keys in `channels.telegram` (no `contacts` field exists)

---

## Gateway is up but behavior is degraded (sessions not saving, heartbeat missing)

**Symptoms:** Gateway responds to `/health`. Adam responds. But sessions aren't persisting, heartbeat isn't arriving, or behavior is inconsistent between sessions.

**Root cause:** Config validation error on hot-reload. The gateway keeps running on stale config but stops processing updates.

**Fix:**
```powershell
Get-Content "C:\tmp\openclaw\openclaw-$(Get-Date -Format 'yyyy-MM-dd').log" |
  Select-String 'invalid config|config reload skipped|Unrecognized key'
```
Any output here is your problem. Fix the flagged key. The gateway hot-reloads on save — no restart needed once the config is clean.

---

## Telegram polling stall / sendMessage failures

**Symptoms:** Gateway log shows:
```
Polling stall detected (no getUpdates for Xs); forcing restart.
telegram sendMessage failed: Network request failed
```

**Root cause:** Network interruption between your machine and Telegram's API servers. Not a gateway bug.

**Fix:** This self-resolves. The gateway detects the stall and restarts the Telegram polling connection automatically. If it persists beyond 5 minutes, check your internet connection. No gateway restart needed.

---

## `nmem_context` / `nmem_recall` return nothing or fail

**Symptoms:** `mcporter call neural-memory.nmem_context` returns empty or errors.

**Fix — Check daemon:**
```powershell
mcporter daemon status
# If not running:
mcporter daemon start
```

**Fix — Check neural-memory version:**
```powershell
python -m pip show neural-memory
# Should show version 4.12.0 or higher
# If outdated: pip install -U neural-memory
```

---

## SENTINEL not starting after reboot

**Symptoms:** Gateway never comes up after a machine restart. Task Scheduler shows the task in `Ready` state but it never ran.

**Fix:**
```powershell
# Check last run result
Get-ScheduledTask -TaskName "ClawdSentinel" | Get-ScheduledTaskInfo

# Force start
Start-ScheduledTask -TaskName "ClawdSentinel"
```

If it consistently fails on boot, the task may need to be re-registered. Run the `register_sentinel.ps1` script from the EMERGENCY_SNAPSHOT directory.

---

## Dual SENTINEL instances causing gateway restart loop

**Symptoms:** Gateway dies every 30-60 seconds in a very regular pattern. Each SENTINEL restart makes it worse.

**Root cause:** Two SENTINEL instances running simultaneously — one from Task Scheduler, one started manually. Each kills the other's gateway process.

**Fix:**
```powershell
# Find all headless PowerShell processes
Get-Process -Name "powershell" | Where-Object { $_.MainWindowTitle -eq "" } | Select-Object Id, StartTime

# Kill the older one (lower PID)
Stop-Process -Id <OLDER_PID> -Force
```

Gateway stabilizes immediately.

---

## openclaw update broke `memory_search`

**Symptoms:** `memory_search` was working, then stopped after running `npm update openclaw` or reinstalling openclaw.

**Root cause:** `npm update` overwrites `extensions/memory-core/index.ts`, reverting the `api.config` patch.

**Fix:** Re-apply the patch:
```powershell
# Verify the patch is missing
Select-String -Path "$env:APPDATA\npm\node_modules\openclaw\extensions\memory-core\index.ts" -Pattern "api\.config"
# No output = patch is gone

# Restore from snapshot
Copy-Item "C:\Users\ajsup\.openclaw\EMERGENCY_SNAPSHOT\extensions\memory-core-index.ts" `
  "$env:APPDATA\npm\node_modules\openclaw\extensions\memory-core\index.ts" -Force

# Restart gateway
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "ClawdSentinel"
```

---

## The Core Rule

> **The gateway fails silently on bad config. It does not crash — it just stops
> reloading and keeps running on stale state.**
>
> If behavior is wrong but the process is alive, check the config log first.
> If the process is dying repeatedly, capture stderr from gateway.cmd first.
> If tools are missing, check both `enabled` flags and the `api.config` patch.

---

*For full production incident writeups with root cause analysis, see `docs/LESSONS_LEARNED.md`.*
