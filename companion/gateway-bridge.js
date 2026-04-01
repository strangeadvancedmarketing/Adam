#!/usr/bin/env node
'use strict';

// gateway-bridge.js — Adapter for Adam's OpenClaw gateway
//
// Polls the gateway's health endpoint and sends status updates to the
// companion overlay via WebSocket. Can also be extended to intercept
// gateway tool calls if the gateway exposes a streaming or log endpoint.
//
// Usage: node gateway-bridge.js
//   Runs continuously. Exits cleanly on SIGINT/SIGTERM.

const WebSocket = require(__dirname + '/node_modules/ws');
const http = require('http');

const GATEWAY_URL = process.env.ADAM_GATEWAY_URL || 'http://localhost:18789';
const POLL_INTERVAL = process.env.ADAM_POLL_INTERVAL || 10000; // 10 seconds
const WS_URL = 'ws://localhost:9876';

let lastGatewayStatus = null;

function checkGateway() {
  const url = GATEWAY_URL + '/health';

  const req = http.get(url, { timeout: 3000 }, (res) => {
    const alive = res.statusCode === 200;
    if (alive !== lastGatewayStatus) {
      lastGatewayStatus = alive;
      sendToCompanion({
        source: 'adam-gateway',
        message: alive ? 'Gateway online' : 'Gateway offline',
        status: alive ? 'active' : 'error',
      });
    }
  });

  req.on('error', () => {
    if (lastGatewayStatus !== false) {
      lastGatewayStatus = false;
      sendToCompanion({
        source: 'adam-gateway',
        message: 'Gateway offline',
        status: 'error',
      });
    }
  });

  req.on('timeout', () => {
    req.destroy();
    if (lastGatewayStatus !== false) {
      lastGatewayStatus = false;
      sendToCompanion({
        source: 'adam-gateway',
        message: 'Gateway timeout',
        status: 'error',
      });
    }
  });
}

function sendToCompanion(payload) {
  const ws = new WebSocket(WS_URL);

  const timeout = setTimeout(() => {
    try { ws.terminate(); } catch (_) {}
  }, 800);

  ws.on('open', () => {
    ws.send(JSON.stringify(payload), () => {
      clearTimeout(timeout);
      ws.close();
    });
  });

  ws.on('error', () => {
    clearTimeout(timeout);
  });
}

// Start polling
checkGateway();
const interval = setInterval(checkGateway, POLL_INTERVAL);

// Clean shutdown
process.on('SIGINT', () => { clearInterval(interval); process.exit(0); });
process.on('SIGTERM', () => { clearInterval(interval); process.exit(0); });

console.log(`Adam gateway bridge started. Polling ${GATEWAY_URL} every ${POLL_INTERVAL}ms`);
