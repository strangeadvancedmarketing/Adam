# Configuration Reference — openclaw.template.json

This file explains every meaningful field in the config template.
You only need to change the fields marked **REQUIRED**. Everything else has working defaults.

---

## env block — API Keys

```json
"env": {
  "LLM_API_KEY": "...",
  "FIRECRAWL_API_KEY": "...",
  "TELEGRAM_BOT_TOKEN": "...",
  "OPENCLAW_GATEWAY_TOKEN": "..."
}
```

| Field | Required | What it is |
|-------|----------|------------|
| `LLM_API_KEY` | **YES** | Your LLM provider API key |
| `FIRECRAWL_API_KEY` | No | Web scraping. Get free at firecrawl.dev. Delete if not using. |
| `TELEGRAM_BOT_TOKEN` | No | Mobile access. Create bot via @BotFather. Delete if not using. |
| `OPENCLAW_GATEWAY_TOKEN` | **YES** | Auth token for your gateway. Generate: `python -c "import secrets; print(secrets.token_hex(16))"` |

---

## models block — Your LLM

```json
"models": {
  "providers": {
    "nvidia": {
      "baseUrl": "https://integrate.api.nvidia.com/v1",
      "apiKey": "YOUR_LLM_API_KEY",
      "api": "openai-completions",
      "models": [...]
    }
  }
}
```

**REQUIRED changes:**
- Change `"nvidia"` to your provider name (can be anything — it's just a label)
- Change `baseUrl` to your provider's API endpoint
- Change `apiKey` to your actual key

**Common provider baseUrls:**
- NVIDIA Developer (free): `https://integrate.api.nvidia.com/v1`
- OpenAI: `https://api.openai.com/v1`
- OpenRouter: `https://openrouter.ai/api/v1`
- Groq: `https://api.groq.com/openai/v1`
- Local Ollama: `http://localhost:11434/v1`

**Model IDs:** Find these in your provider's model catalog. The `id` field must exactly match what the API expects.

---

## agents.defaults.model — Active Model

```json
"model": {
  "primary": "nvidia/moonshotai/kimi-k2.5"
}
```

**REQUIRED:** Change this to `YOUR_PROVIDER_NAME/YOUR_MODEL_ID`.
This must match the provider name and model id you set in the `models` block above.

---

## agents.defaults.memorySearch.extraPaths — Vault Connection

```json
"extraPaths": [
  "C:\\YOUR_VAULT_PATH\\CORE_MEMORY.md",
  "C:\\YOUR_VAULT_PATH\\workspace\\memory",
  "C:\\YOUR_VAULT_PATH\\workspace\\BOOT_CONTEXT.md"
]
```

**REQUIRED:** Replace `YOUR_VAULT_PATH` with your actual Vault directory path.
Use double backslashes on Windows. Example: `C:\\MyAIVault`

This is how OpenClaw indexes your identity files and memory logs.
`BOOT_CONTEXT.md` is compiled by SENTINEL — it won't exist until you run SENTINEL once.

---

## agents.defaults.memorySearch.query — Hybrid Search Tuning

```json
"query": {
  "hybrid": {
    "enabled": true,
    "vectorWeight": 0.7,
    "textWeight": 0.3,
    "candidateMultiplier": 4
  }
}
```

**Leave these as-is.** These are tuned defaults from production use.
- `vectorWeight 0.7 / textWeight 0.3` — 70% semantic similarity, 30% exact text match. Best balance for conversational context retrieval.
- `candidateMultiplier 4` — retrieves 4x the final result count before re-ranking. Better accuracy at minimal cost.

---

## agents.defaults.compaction.memoryFlush — Layer 4 (The Core Solve)

```json
"memoryFlush": {
  "enabled": true,
  "softThresholdTokens": 4000,
  "prompt": "Write any lasting notes to C:\\YOUR_VAULT_PATH\\workspace\\memory\\YYYY-MM-DD.md...",
  "systemPrompt": "You are YOUR_AI_NAME. Session nearing compaction. Store durable memories now."
}
```

**REQUIRED:** Update `YOUR_VAULT_PATH` in `prompt` and `YOUR_AI_NAME` in `systemPrompt`.

This is the compaction flush — it triggers when the session context is within 4,000 tokens of the limit. The AI writes durable notes to the daily log before truncation. This is the mechanism that prevents information loss at session boundaries.

`softThresholdTokens: 4000` means the flush triggers when 4,000 tokens remain. Leave this value — lower means less buffer, higher means earlier writes.

---

## agents.defaults.blockStreamingChunk — Message Chunking

```json
"blockStreamingChunk": {
  "minChars": 1200,
  "maxChars": 1400
}
```

**Leave as-is** unless you're using TTS. These values control how the AI splits long responses into chunks. Critical for voice output — each chunk becomes a separate voice message, and the limits prevent voice cutoffs.

If you're not using TTS, you can raise `maxChars` to 4000+ for longer unbroken responses.

---

## messages.tts — Voice Output

```json
"messages": {
  "tts": {
    "auto": "always",
    "provider": "edge",
    "edge": {
      "enabled": true,
      "voice": "en-GB-RyanNeural"
    }
  }
}
```

**Not using voice?** Delete the entire `messages` block.

**Using voice?** The `edge` provider uses Microsoft Edge TTS — no API key needed, works on any Windows machine with Edge installed.

Available voices: run `edge-tts --list-voices` in PowerShell after `pip install edge-tts`.
Common voices: `en-US-GuyNeural`, `en-GB-RyanNeural`, `en-US-JennyNeural`

---

## channels.telegram — Mobile Access

```json
"channels": {
  "telegram": {
    "enabled": true,
    "botToken": "YOUR_TELEGRAM_BOT_TOKEN",
    "dmPolicy": "open",
    "allowFrom": ["*"]
  }
}
```

**Not using Telegram?** Delete the entire `channels` block.

**Using Telegram:**
1. Message @BotFather on Telegram → `/newbot`
2. Follow prompts, copy the token
3. Set `botToken` to your token
4. `dmPolicy: "open"` means anyone can DM the bot — change to `"allowlist"` and add your user ID to restrict access

---

## gateway — Port and Auth

```json
"gateway": {
  "port": 18789,
  "mode": "local",
  "auth": {
    "mode": "token",
    "token": "YOUR_GENERATED_TOKEN"
  }
}
```

**REQUIRED:** Set `token` to the same value you set in `OPENCLAW_GATEWAY_TOKEN` above.

`port: 18789` — you can change this if the port is taken. Update SENTINEL.ps1 accordingly.
`mode: "local"` — for local desktop use. Change to `"server"` for headless/cloud deployment.

---

## plugins — Active OpenClaw Plugins

```json
"plugins": {
  "allow": ["telegram", "memory-core"],
  "entries": {
    "memory-core": { "enabled": true },
    "telegram": { "enabled": true }
  }
}
```

**Leave as-is** for the base setup.

**To add email:** Add `"email"` to the `allow` array and add an email entry block:
```json
"email": {
  "enabled": true,
  "config": {
    "username": "your@gmail.com",
    "appPassword": "your-gmail-app-password",
    "imapHost": "imap.gmail.com",
    "smtpHost": "smtp.gmail.com"
  }
}
```
Note: Gmail requires an App Password, not your regular password. Create one at myaccount.google.com → Security → App Passwords.
