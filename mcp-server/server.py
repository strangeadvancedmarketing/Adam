#!/usr/bin/env python3
"""
Adam Framework MCP Server

Exposes Adam's vault memory as MCP tools usable in Claude Desktop,
Cursor, Windsurf, or any MCP-compatible client.

Tools:
  memory_search  - Search vault markdown files by keyword
  memory_get     - Retrieve a specific vault file by name
  memory_list    - List all memory files in the vault

Usage:
  Set ADAM_VAULT_PATH env var to your vault directory.
  Default: ~/AdamsVault/workspace

Install:
  pip install mcp

Run:
  python server.py
  or add to mcpServers in claude_desktop_config.json
"""

import os
import re
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Vault path from env or default
VAULT_PATH = Path(os.environ.get("ADAM_VAULT_PATH", Path.home() / "AdamsVault" / "workspace"))

app = Server("adam-memory")

def get_memory_files() -> list[Path]:
    """Get all markdown files from vault memory directories."""
    files = []
    search_dirs = [
        VAULT_PATH,
        VAULT_PATH / "memory",
        VAULT_PATH / "scripture",
    ]
    for d in search_dirs:
        if d.exists():
            files.extend(d.glob("*.md"))
            files.extend(d.glob("*.json"))
    # Also include root vault md files
    if VAULT_PATH.parent.exists():
        for f in VAULT_PATH.parent.glob("*.md"):
            if f not in files:
                files.append(f)
    return sorted(set(files))

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="memory_search",
            description="Search Adam's vault memory files by keyword. Returns matching excerpts with file names and line numbers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - keyword or phrase to find in memory files"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="memory_get",
            description="Retrieve the full contents of a specific vault memory file by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "File name to retrieve (e.g. 'CORE_MEMORY.md', 'Adam_Core_Memory.md')"
                    }
                },
                "required": ["filename"]
            }
        ),
        types.Tool(
            name="memory_list",
            description="List all memory files available in the Adam vault.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "memory_search":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        results = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        
        for filepath in get_memory_files():
            try:
                text = filepath.read_text(encoding="utf-8", errors="ignore")
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if pattern.search(line):
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 3)
                        context = "\n".join(lines[context_start:context_end])
                        results.append({
                            "file": filepath.name,
                            "line": i + 1,
                            "context": context.strip()
                        })
                        if len(results) >= max_results:
                            break
            except Exception:
                continue
            if len(results) >= max_results:
                break
        
        if not results:
            return [types.TextContent(type="text", text=f"No results found for '{query}'")]
        
        output = f"Found {len(results)} result(s) for '{query}':\n\n"
        for r in results:
            output += f"[{r['file']} line {r['line']}]\n{r['context']}\n\n---\n\n"
        return [types.TextContent(type="text", text=output)]

    elif name == "memory_get":
        filename = arguments.get("filename", "")
        # Search all memory file locations
        for filepath in get_memory_files():
            if filepath.name.lower() == filename.lower():
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    return [types.TextContent(type="text", text=f"# {filepath.name}\n\n{content}")]
                except Exception as e:
                    return [types.TextContent(type="text", text=f"Error reading {filename}: {e}")]
        return [types.TextContent(type="text", text=f"File '{filename}' not found in vault. Use memory_list to see available files.")]

    elif name == "memory_list":
        files = get_memory_files()
        if not files:
            return [types.TextContent(type="text", text=f"No memory files found in vault at: {VAULT_PATH}")]
        file_list = "\n".join(f"- {f.name} ({f.stat().st_size} bytes)" for f in files)
        return [types.TextContent(type="text", text=f"Adam vault memory files ({len(files)} total):\n\n{file_list}")]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
