const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');

let mainWindow;
let wss;

// --- Vault status polling ---
// Reads vault files to show system health in the overlay.
// All reads are safe — these files are meant to be consumed.

const VAULT_PATH = process.env.ADAM_VAULT_PATH || path.join(require('os').homedir(), 'AdamsVault', 'workspace');

function readVaultStatus() {
  const status = {};

  // Read TODAY.md for current date
  try {
    const today = fs.readFileSync(path.join(VAULT_PATH, 'TODAY.md'), 'utf8').trim();
    status.today = today;
  } catch (_) {}

  // Read coherence baseline for last check time
  try {
    const baseline = JSON.parse(fs.readFileSync(path.join(VAULT_PATH, 'coherence_baseline.json'), 'utf8'));
    status.coherenceScore = baseline.drift_score;
    status.lastCoherenceCheck = baseline.timestamp;
  } catch (_) {}

  // Read neural metrics for graph size
  try {
    const metrics = JSON.parse(fs.readFileSync(path.join(VAULT_PATH, 'neural_metrics.json'), 'utf8'));
    if (Array.isArray(metrics) && metrics.length > 0) {
      const latest = metrics[metrics.length - 1];
      status.neurons = latest.neurons;
      status.synapses = latest.synapses;
    }
  } catch (_) {}

  // Check if gateway is alive
  try {
    const http = require('http');
    const req = http.get('http://localhost:18789/health', { timeout: 2000 }, (res) => {
      status.gatewayAlive = res.statusCode === 200;
      sendStatusToRenderer(status);
    });
    req.on('error', () => {
      status.gatewayAlive = false;
      sendStatusToRenderer(status);
    });
    req.on('timeout', () => {
      req.destroy();
      status.gatewayAlive = false;
      sendStatusToRenderer(status);
    });
    return; // async — status sent inside callback
  } catch (_) {
    status.gatewayAlive = false;
  }

  sendStatusToRenderer(status);
}

function sendStatusToRenderer(status) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('vault-status', status);
  }
}

// --- Window creation ---

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  const windowWidth = 300;
  const windowHeight = 420;
  const margin = 16;

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: screenWidth - windowWidth - margin,
    y: screenHeight - windowHeight - margin,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile('index.html');
  mainWindow.setIgnoreMouseEvents(false);

  ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
    mainWindow.setIgnoreMouseEvents(ignore, options || { forward: true });
  });

  // Poll vault status every 30 seconds
  readVaultStatus();
  setInterval(readVaultStatus, 30000);
}

// --- WebSocket server ---
// Receives events from:
//   1. Claude Code PostToolUse hook (hook-bridge.js)
//   2. Adam gateway adapter (gateway-bridge.js)
//   3. Any external process sending JSON to ws://localhost:9876

function startWebSocketServer() {
  wss = new WebSocket.Server({ port: 9876 });

  wss.on('connection', (ws) => {
    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('hook-event', message);
        }
      } catch (e) {
        // ignore malformed messages
      }
    });

    ws.on('error', () => {});
  });

  wss.on('error', (err) => {
    if (err.code !== 'EADDRINUSE') {
      console.error('WebSocket server error:', err.message);
    }
  });
}

// --- App lifecycle ---

app.whenReady().then(() => {
  createWindow();
  startWebSocketServer();
});

app.on('window-all-closed', () => {
  if (wss) wss.close();
  app.quit();
});
