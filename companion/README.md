# Adam Companion

A desktop overlay that shows what your Adam Framework agent is doing in real time.

## What It Does

The Adam Companion is a transparent, always-on-top desktop widget that sits in the corner of your screen. It shows:

- Real-time tool activity (file reads, searches, web fetches, memory operations)
- Gateway status (online/offline)
- Neural graph size
- Coherence state

Works with both the Adam Framework gateway and Claude Code.

## Quick Start

```bash
cd companion
npm install
npm start
```

## Integration

### With Claude Code

Add to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node /path/to/Adam/companion/hook-bridge.js",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

### With Adam Gateway

Run the gateway bridge alongside the companion:

```bash
node gateway-bridge.js
```

This polls the gateway health endpoint and sends status updates to the overlay.

### From Any Process

Send JSON to `ws://localhost:9876`:

```json
{"tool_name": "Read", "tool_input": {"file_path": "vault/CORE_MEMORY.md"}}
```

or:

```json
{"message": "Checking email...", "source": "adam-gateway"}
```

## Architecture

```
companion/
├── main.js            # Electron main process + WebSocket server + vault poller
├── preload.js         # Secure IPC bridge
├── index.html         # Robot UI + event formatting + status bar
├── hook-bridge.js     # Claude Code hook → WebSocket sender
├── gateway-bridge.js  # Adam gateway health → WebSocket sender
└── package.json
```

**Ports used:** WebSocket on `localhost:9876` only. No other network calls.

**Files read (never written):** `BOOT_CONTEXT.md`, `coherence_baseline.json`, `neural_metrics.json`, `TODAY.md` from the vault.

## SENTINEL Integration

If you want SENTINEL to manage the companion process, add these lines after the gateway launch section in your SENTINEL script:

**PowerShell (Windows):**
```powershell
# Launch companion overlay
$companionPath = Join-Path $PSScriptRoot ".." "companion"
if (Test-Path (Join-Path $companionPath "node_modules")) {
    Start-Process -NoNewWindow -FilePath "npx" -ArgumentList "electron ." -WorkingDirectory $companionPath
    Write-Log "Companion overlay launched"
}
```

**Bash (Linux/macOS):**
```bash
# Launch companion overlay
COMPANION_DIR="$(dirname "$0")/../companion"
if [ -d "$COMPANION_DIR/node_modules" ]; then
    cd "$COMPANION_DIR" && npx electron . &
    echo "[SENTINEL] Companion overlay launched"
fi
```

## License

MIT — same as the Adam Framework.
