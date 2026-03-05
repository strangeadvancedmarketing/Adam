# Lessons Learned

> Production failure log for the Adam Framework.
> Every entry here was a real system break. Root causes, symptoms, and confirmed fixes.
> If something breaks in your deployment, start here.

---

## [2026-03-05] Invalid config key causes silent gateway reload loop

### Symptom
Gateway logs fill with:
```
[session-store] rename failed after 5 attempts: ...sessions.json
```
Heartbeat fails with `chat not found`. Sessions save inconsistently.
System appears to be running but behavior is degraded.

### Root Cause
An unrecognized key was present in `channels.telegram` in `openclaw.json`:
```json
"contacts": {
  "heartbeat": "-100xxxxxxxxxx:topic:1409"
}
```
OpenClaw's config validator rejected the key on every hot-reload with:
```
Invalid config: channels.telegram: Unrecognized key: "contacts"
config reload skipped (invalid config)
```
Because the config reload was failing, the gateway kept running on its stale
in-memory config — but every session write attempt hit a filesystem contention
cascade from the failed reload loop.

The `contacts` field does **not exist** in the `channels.telegram` schema.
It was added based on a reasonable assumption that proved incorrect.

### How To Route Heartbeats to a Telegram Topic
The correct schema is `agents.defaults.heartbeat` with `target` and `to` fields:

```json
"agents": {
  "defaults": {
    "heartbeat": {
      "every": "30m",
      "target": "telegram",
      "to": "-1003764282014:topic:1409",
      "activeHours": {
        "start": "07:00",
        "end": "24:00",
        "timezone": "America/New_York"
      }
    }
  }
}
```

For Telegram topics/threads the `to` format is `<chatId>:topic:<messageThreadId>`.

### How to Catch This Class of Error
If the gateway is running but behavior is degraded, always check:
```powershell
Get-Content C:\tmp\openclaw\openclaw-$(Get-Date -Format 'yyyy-MM-dd').log |
  Select-String 'invalid config|config reload skipped|Unrecognized key'
```
Config validation errors do **not** crash the gateway — they fail silently and
leave the system running on stale config. You won't see an obvious crash.

### Fix Applied
- Removed `contacts` block from `channels.telegram`
- Added correct `agents.defaults.heartbeat` block with `target: "telegram"` and `to: "CHAT_ID:topic:THREAD_ID"`
- Updated `engine/openclaw.template.json` to reflect correct pattern
- Documented in `CHANGELOG.md` as v1.0.2

---

## [2026-03-05] session-store rename failures caused by MCP filesystem handle retention

### Symptom
Gateway logs continue to show:
```
[session-store] rename failed after 5 attempts: ...sessions.json
```
This persists even after fixing the invalid config key (see entry above).
Errors resume within seconds of every gateway restart.

### Root Cause
The Claude desktop app (or any MCP client with filesystem access) was holding
persistent open file handles on `sessions.json` via the Desktop Commander MCP
integration. Windows does not allow atomic rename operations (`fs.rename()`) when
the destination file is held open by another process — even a read handle blocks it.

Identified via Sysinternals `handle64.exe`:
```
handle64 -p <gateway_pid> sessions.json
```
Output showed `claude.exe` (PID 1076) with two open handles — acquired during
earlier diagnostic `read_file` calls in the same session — that were never released
because the MCP client holds handles for the lifetime of the conversation session.

This is a Windows-specific behavior. On Linux/macOS, rename over an open file
succeeds because inodes are unlinked, not locked. On Windows, the file must be
closed before it can be replaced.

### Fix Applied
Removed `.openclaw\agents` from Desktop Commander's `allowedDirectories` config:
```json
"allowedDirectories": [
  "C:\\Users\\AJSup\\Desktop",
  "C:\\Users\\AJSup\\adam-framework-public",
  "C:\\Users\\AJSup\\AppData\\Roaming\\npm",
  "C:\\AdamsVault",
  "C:\\Users\\AJSup\\.openclaw"
]
```
The sessions subdirectory is excluded — MCP tools can no longer open those files.
New sessions start clean with zero handles on the sessions directory.

### How To Diagnose This In Your Deployment
If rename errors persist after fixing config issues, run:
```powershell
# Download handle64 from Sysinternals if not present
# Then:
& "C:\path\to\handle64.exe" -p (Get-Process -Name "openclaw*").Id sessions.json
```
If any process other than the gateway itself has handles open, that's your culprit.
Scope it out of whatever filesystem access tool is holding it.

### Key Insight
> MCP filesystem integrations that allow broad directory access will acquire and
> hold read handles for the duration of the client session. On Windows this silently
> blocks atomic writes in those directories. Scope `allowedDirectories` precisely —
> only what actually needs to be touched, nothing broader.

---

## [2026-02-XX] SENTINEL watchdog failing to restart after crash

### Symptom
Gateway goes offline. SENTINEL scheduled task shows "last run failed."
System doesn't auto-recover.

### Root Cause
`openclaw.json` had an invalid key in the `mcp.servers` vs `mcpServers` namespace
(OpenClaw uses `mcp.servers`, not the `mcpServers` used by some other tools).
The gateway crashed on load rather than starting degraded, and SENTINEL's restart
logic couldn't distinguish a bad-config crash from a transient failure.

### Fix Applied
Corrected the MCP server key in `openclaw.json`. Added startup validation
to SENTINEL to check gateway health after restart before marking recovery complete.

---

## [2026-02-XX] Delivery queue filled with stale failed heartbeat entries

### Symptom
Heartbeat messages stop arriving in Telegram. No crash, no obvious error.
Gateway appears healthy.

### Root Cause
45 stale failed heartbeat delivery entries accumulated in the delivery queue
(`~/.openclaw/delivery/`). The queue processor was retrying them indefinitely,
backing up all new deliveries behind them.

### Fix Applied
Cleared stale entries from the delivery queue directory. Added queue inspection
to the regular health check routine.

---

## General Debugging Checklist

When something breaks and you don't know where:

1. **Check the day's gateway log for config errors first:**
   ```powershell
   Get-Content C:\tmp\openclaw\openclaw-$(Get-Date -Format 'yyyy-MM-dd').log |
     Select-String 'ERROR|invalid config|Unrecognized key|reload skipped'
   ```

2. **Validate `openclaw.json` is clean JSON before touching anything else:**
   ```powershell
   Get-Content C:\Users\YOU\.openclaw\openclaw.json -Raw | ConvertFrom-Json | Out-Null
   ```
   Any error here is your starting point.

3. **Check the delivery queue for buildup:**
   ```powershell
   (Get-ChildItem C:\Users\YOU\.openclaw\delivery\).Count
   ```
   More than ~5 files is a sign of queue backup.

4. **Confirm SENTINEL is running:**
   ```powershell
   Get-ScheduledTask -TaskName 'OpenClaw*' | Select-Object TaskName, State, LastRunTime
   ```

5. **If config was recently changed:** assume the change is the cause. Revert first,
   verify the gateway recovers, then re-apply the change correctly.

---

## The Core Rule

> **The gateway fails silently on bad config. It does not crash — it just stops
> reloading and keeps running on stale state.**
>
> If behavior is wrong but the process is alive, check the config first.
