# Hindsight MemPalace MCP Server

Standalone [MCP](https://modelcontextprotocol.io) server that exposes Hindsight MemPalace memory tools to any MCP-compatible client (Claude Code, OpenClaw, etc).

## Tools

| Tool | Description |
|------|-------------|
| `memory_retain` | Save memories with room/hall/layer classification |
| `memory_recall` | Scoped semantic search with room filtering |
| `memory_reflect` | Deep reasoning + synthesis over stored memories |
| `memory_compress` | Create closet summaries from accumulated facts |
| `memory_bridge` | Cross-bank tunnels between related memories |

## Quick Start

```bash
cd mcp-server
npm install
HINDSIGHT_URL=http://localhost:5100 node server.js
```

## Claude Code

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "node",
      "args": ["/path/to/mcp-server/server.js"],
      "env": {
        "HINDSIGHT_URL": "http://localhost:5100",
        "MEMPALACE_BANK": "my-agent-bank"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HINDSIGHT_URL` | `http://127.0.0.1:5100` | Hindsight API base URL |
| `MEMPALACE_BANK` | `mempalace-main` | Default memory bank ID |

## MemPalace Taxonomy

**Rooms** (topics): auth, pipeline, schema, infrastructure, ui, api, deployment, monitoring, agent, general

**Halls** (knowledge types): fact, event, decision, preference, discovery, procedure, warning

**Layers** (priority):
- L0 — Critical (always recalled)
- L1 — Important (recalled by default)
- L2 — Normal (default for new memories)
- L3 — Archive (deep search only, compressed into closets)
