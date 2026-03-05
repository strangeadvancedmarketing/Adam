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

---

## [2026-03-05] SENTINEL vector reindex hitting nonexistent HTTP endpoint (405)

### Symptom
Every SENTINEL boot produces a non-fatal error in the log:
```
[SENTINEL] Vector reindex failed (non-fatal): The remote server returned an error: (405) Method Not Allowed.
```
System continues booting and Adam responds normally. But memory written by the
sleep cycle (reconcile run) is not indexed into the vector store — `memory_search`
misses content from the current cycle until a manual `openclaw memory index` is run.

### Root Cause
`SENTINEL.template.ps1` (and live SENTINEL instances built from it) called
`POST /api/memory/reindex` on the OpenClaw gateway after confirming gateway health.
That HTTP endpoint does not exist in OpenClaw. The gateway returns 405 Method Not
Allowed. OpenClaw does not expose a REST API for memory reindex operations.

### Fix
Replace the `Invoke-WebRequest` reindex block with a direct CLI call:

```powershell
# BEFORE (broken — endpoint does not exist)
$ocCfg   = Get-Content "$OPENCLAW_DIR\openclaw.json" -Raw | ConvertFrom-Json
$token   = $ocCfg.gateway.auth.token
$headers = @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
$body    = '{"scope":"vault","path":"' + $VAULT_PATH + '"}'
Invoke-WebRequest -Uri "http://localhost:18789/api/memory/reindex" `
    -Method POST -Headers $headers -Body $body -TimeoutSec 30 -ErrorAction Stop | Out-Null

# AFTER (correct — use the CLI directly)
$reindexResult = & openclaw memory index --agent main 2>&1 | Out-String
```

The CLI command `openclaw memory index --agent main` is the documented approach.
No HTTP endpoint, no auth token, no gateway dependency beyond it being live.

### How To Confirm
After applying the fix and restarting SENTINEL, the log should show:
```
[SENTINEL] Vector reindex triggered successfully.
```
instead of the 405 error.

### Key Insight
> **OpenClaw does not expose REST endpoints for all CLI operations.**
> When SENTINEL needs to trigger a gateway-side action, always check the CLI docs
> (`openclaw help <command>`) before assuming an HTTP route exists.
> `openclaw memory index`, `openclaw memory status`, etc. are CLI-only — not REST.

---

## [2026-03-05] coherence_monitor score_drift fall-through causes false positives and BOOT_CONTEXT bloat

### Symptom
Adam's response latency increases noticeably. Sentinel log shows drift detected and
re-anchor fired every 5 minutes even in active, coherent sessions:
```
[2026-03-05 16:38:56] Coherence check: exit 1
[2026-03-05 16:38:56] DRIFT DETECTED - consuming re-anchor...
[2026-03-05 16:43:57] Coherence check: exit 1
[2026-03-05 16:43:57] DRIFT DETECTED - consuming re-anchor...
```
BOOT_CONTEXT.md grows every 5 minutes. Running `coherence_monitor.py` directly
shows `Scratchpad in last 10 turns: True` alongside `Drift score: 0.9` — a
contradiction. Scratchpad active + maximum drift score = bug in the scorer.

### Root Cause
`score_drift()` used a chain of independent `if` statements rather than `if/elif/else`.
The function had four explicit branches but no coverage for `scratchpad_present=True`
with `CONTEXT_DRIFT_THRESHOLD <= context_pct < CONTEXT_WARN_THRESHOLD` (40–65%).

When context depth crossed 40%, all four `if` conditions evaluated to `False`:
- `scratchpad_present and context_pct < 0.40` → False (context too high)
- `scratchpad_present and context_pct >= 0.65` → False (context not high enough)
- `not scratchpad_present and ...` → False (scratchpad IS present)

With all branches missed, execution fell through to the final `return 0.9` catch-all
(intended for "scratchpad absent + high context"). Every session at 40%+ context with
an active scratchpad scored as maximum drift — the opposite of reality.

`should_reanchor()` also checked `context_pct >= CONTEXT_WARN_THRESHOLD` as an
independent trigger, meaning deep context alone could fire re-anchor even when the
scratchpad was firing correctly.

### Cascade
False positive drift (exit 1) every 5 minutes → SENTINEL appends re-anchor block
(~200 tokens) to BOOT_CONTEXT.md → file grows from ~21KB to ~23KB → Adam loads
larger context on every message → response latency increases → eventually gateway
timeouts produce `stopReason: "error"` turns with `usage.input: 0` → coherence
monitor reads zero tokens as further evidence of drift → loop continues.

### Fix
Replaced chained `if` statements with exhaustive `if/elif/else` on the
`scratchpad_present` branch:

```python
# BEFORE (broken — fall-through to catch-all)
if scratchpad_present and context_pct < CONTEXT_DRIFT_THRESHOLD:
    return 0.0
if scratchpad_present and context_pct >= CONTEXT_WARN_THRESHOLD:
    return 0.4
if not scratchpad_present and context_pct < CONTEXT_DRIFT_THRESHOLD:
    return 0.3
...
return 0.9  # ← was hit for scratchpad_present=True, 40-65% context

# AFTER (exhaustive — no fall-through possible)
if scratchpad_present:
    if context_pct < CONTEXT_DRIFT_THRESHOLD:   return 0.0
    elif context_pct < CONTEXT_WARN_THRESHOLD:  return 0.2  # new branch
    else:                                        return 0.4
else:
    if context_pct < CONTEXT_DRIFT_THRESHOLD:   return 0.3
    elif context_pct < CONTEXT_WARN_THRESHOLD:  return 0.6
    else:                                        return 0.9
```

`should_reanchor()` simplified to `return drift_score >= 0.6` — context depth alone
never triggers re-anchor when the scratchpad is firing.

### Recovery Steps
1. Apply fix to `tools/coherence_monitor.py`
2. Clear any pending re-anchor: open `workspace/reanchor_pending.json`, set `consumed: true`
3. Recompile BOOT_CONTEXT.md cleanly (run SENTINEL boot or manually execute the
   compile block from `SENTINEL.ps1`)
4. Verify: `python tools/coherence_monitor.py` should return exit 0 with
   `Drift score: 0.2` (not 0.9) for a healthy mid-context session

### How To Detect This Class of Error
If coherence monitor fires exit 1 repeatedly but logs show `Scratchpad... True`:
```powershell
python tools\coherence_monitor.py
# If output shows "Scratchpad in last 10 turns: True" AND "Drift score: 0.9"
# that's a scorer bug, not real drift.
```
Check BOOT_CONTEXT.md line count — more than ~480 lines means re-anchor blocks
have been appended. Recompile it.

### Key Insight
> **A scoring function with independent `if` branches instead of `if/elif/else`
> will silently fall through to a catch-all when input falls in an unhandled range.
> Always verify scoring functions with exhaustive unit tests covering every branch,
> including boundary values.**

The missing test was `score_drift(True, 0.50)` — scratchpad present, mid-context.
That exact case is now in `test_coherence_monitor.py` as `test_scratchpad_present_mid_context`
and `test_no_fallthrough_exhaustive`. Test count: 27 → 30.

---

## [2026-03-05] Dual SENTINEL instances causing gateway watchdog loop

### Symptom
Gateway dies every 30-60 seconds. SENTINEL watchdog catches it and immediately
restarts — but the gateway dies again within the minute. Sentinel log shows repeated:
```
WARNING: Gateway process died. Restarting...
Gateway started - PID XXXXX
```
Killing and restarting SENTINEL seems to fix it but the problem returns.

### Root Cause
Two SENTINEL instances running simultaneously. One started manually (e.g., direct
PowerShell invocation for testing), a second spawned by Task Scheduler. Both
instances watch for a dead gateway — but each one's watchdog kills the gateway
process that the *other* started, because the gateway process was launched by the
other instance and has a different PID reference.

Both watchdogs see a dead process → both restart the gateway → both kill the other's
restart → loop repeats indefinitely at 30-second intervals.

### How To Diagnose
```powershell
Get-Process -Name "powershell" | Select-Object Id, StartTime, MainWindowTitle
```
If you see two powershell processes both with similar start times and no window
titles, you have a dual-SENTINEL situation. Confirm by checking:
```powershell
Get-Content "$env:USERPROFILE\.openclaw\sentinel.log" -Tail 20
```
If the log shows gateway dying and restarting at exact 30s intervals, that's
the watchdog-vs-watchdog pattern.

### Fix
Kill the older SENTINEL process (lower PID = older). Keep the one started by
Task Scheduler — it's the authoritative one and will restart at next login.

```powershell
# Find the older PID and kill it
Stop-Process -Id <OLDER_PID> -Force
```

Gateway stabilizes immediately once only one watchdog is running.

### Prevention
Always check for running SENTINEL instances before launching manually:
```powershell
Get-Process -Name "powershell" | Where-Object { $_.MainWindowTitle -eq "" }
```
If any headless PowerShell processes exist, SENTINEL may already be running.
Check `sentinel.log` to confirm before launching a second instance.

---

## [2026-03-05] Kokoro TTS permanently removed

### Symptom
SENTINEL log fills with Kokoro restart attempts even when the system is otherwise
healthy. `kokoro.exe` or `python server.py` crashes silently, SENTINEL detects it
and restarts, it crashes again. No voice output. Loop continues indefinitely.

### Root Cause
Kokoro TTS has persistent stability issues — version mismatches, model file path
problems, port conflicts, and silent crashes that are difficult to diagnose. The
restart loop consumes log space and SENTINEL overhead without providing value.

### Resolution (Permanent)
Kokoro TTS removed from SENTINEL entirely. Edge TTS is the default voice layer —
it's stable, zero-config, no external process to monitor, and produces acceptable
quality for all current use cases.

`SENTINEL.template.ps1` v1.0.9 has zero Kokoro references. If you copied an older
version of the template, remove:
- `$USE_KOKORO`, `$PYTHON_EXE` (if only used for Kokoro), `$KOKORO_DIR`, `$KOKORO_LOG`, `$KOKORO_ERR` variables
- `Start-Kokoro` function
- The `if ($USE_KOKORO)` block in the process kill section
- The `$kokoro = Start-Kokoro` call after gateway launch
- The Kokoro watchdog restart block inside the while loop

Edge TTS requires no configuration — it's built into Windows and works out of the
box with OpenClaw's TTS provider block.
