# Adam Framework MCP Server

Exposes Adam's persistent vault memory as MCP tools, usable in Claude Desktop, Cursor, Windsurf, or any MCP-compatible client.

## Install

```bash
pip install adam-mcp
```

## Tools

| Tool | Description |
|------|-------------|
| `memory_search` | Search vault markdown files by keyword — returns excerpts with file names and line numbers |
| `memory_get` | Retrieve the full contents of a specific vault file by name |
| `memory_list` | List all memory files available in the vault |

## Quick Start

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "adam-memory": {
      "command": "python",
      "args": ["-m", "adam_mcp"],
      "env": {
        "ADAM_VAULT_PATH": "C:/path/to/your/vault"
      }
    }
  }
}
```

Restart Claude Desktop. You'll see `memory_search`, `memory_get`, and `memory_list` available in your next session.

### Works with any markdown folder

Point `ADAM_VAULT_PATH` at any folder of `.md` files — an Obsidian vault, exported Notion pages, plain notes. No Adam setup required.

### Docker

```bash
docker build -t adam-mcp .
docker run -e ADAM_VAULT_PATH=/vault -v C:/path/to/your/vault:/vault adam-mcp
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADAM_VAULT_PATH` | `~/vault` | Path to your vault directory containing markdown memory files |

---

## Want the full experience?

This MCP server gives Claude Desktop read access to your vault. The full Adam Framework goes further:

- **Persistent identity** — your AI knows who it is and who you are before you say a word
- **Nightly reconciliation** — daily logs consolidated into structured memory while you sleep
- **Neural memory graph** — 16,000+ concept nodes with associative recall, not just keyword search
- **Coherence monitor** — detects and corrects context drift mid-session
- **Onboarding wizard** — 5 questions, auto-generates your full identity and behavioral constitution

**[⚡ Fast-Track Setup — $49](https://strangemarket.gumroad.com/l/adam-framework)**
Get the full Adam Framework configured and running on your machine. Includes vault structure, SENTINEL boot system, reconcile cycle, and everything wired together.

---

## About

The Adam Framework is a 5-layer persistent memory and identity architecture for local AI agents.
The memory lives in plain markdown files you own. The model is just the reader.

[Full framework →](https://github.com/strangeadvancedmarketing/Adam)