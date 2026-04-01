#!/usr/bin/env node
'use strict';

// hook-bridge.js — Called by Claude Code PostToolUse hook
// Reads JSON from stdin, sends it to the companion WebSocket overlay, exits fast.
// Also works as a general-purpose bridge for any process that pipes JSON to stdin.

const WebSocket = require(__dirname + '/node_modules/ws');

let inputData = '';

process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { inputData += chunk; });

process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(inputData);
  } catch (e) {
    process.exit(0);
  }

  const ws = new WebSocket('ws://localhost:9876');

  const timeout = setTimeout(() => {
    try { ws.terminate(); } catch (_) {}
    process.exit(0);
  }, 800);

  ws.on('open', () => {
    ws.send(JSON.stringify(payload), () => {
      clearTimeout(timeout);
      ws.close();
      process.exit(0);
    });
  });

  ws.on('error', () => {
    clearTimeout(timeout);
    process.exit(0);
  });
});
