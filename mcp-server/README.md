# Adam Framework MCP Server

Exposes Adam's persistent vault memory as MCP tools, usable in Claude Desktop, Cursor, Windsurf, or any MCP-compatible client.

## Tools

| Tool | Description |
|------|-------------|
| `memory_search` | Search vault markdown files by keyword — returns excerpts with file names and line numbers |
| `memory_get` | Retrieve the full contents of a specific vault file by name |
| `memory_list` | List all memory files available in the vault |

## Quick Start

### Claude Desktop (stdio)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "adam-memory": {
      "command": "python",
      "args": ["C:/path/to/adam-mcp-server/server.py"],
      "env": {
        "ADAM_VAULT_PATH": "C:/AdamsVault/workspace"
      }
    }
  }
}
```

### Docker

```bash
docker build -t adam-mcp .
docker run -e ADAM_VAULT_PATH=/vault -v C:/AdamsVault/workspace:/vault adam-mcp
```

### Install dependencies

```bash
pip install mcp
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADAM_VAULT_PATH` | `~/AdamsVault/workspace` | Path to your Adam vault workspace directory |

## About

The Adam Framework is a 5-layer persistent memory and identity architecture for local AI agents.
The memory lives in plain markdown files you own. The model is just the reader.

[Full framework →](https://github.com/strangeadvancedmarketing/Adam)
