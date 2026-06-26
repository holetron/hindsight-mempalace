# Hindsight MemPalace

**Hierarchical memory for AI agents. Storage + taxonomy in one system.**

A hybrid of two open-source projects:

| Project | What it does | What it lacks |
|---|---|---|
| [**Hindsight**](https://github.com/vectorize-io/hindsight) by vectorize-io | Long-term vector memory for AI agents. Stores, embeds, recalls. | No structure — all memories in one flat pile |
| [**MemPalace**](https://github.com/milla-jovovich/mempalace) by milla-jovovich | Hierarchical taxonomy: rooms, halls, layers — the method of loci for AI | No storage engine — a spec without a database |

**This fork connects them.** Hindsight's vector store + MemPalace's taxonomy = structured memory with semantic search.

---

## How it works

```
┌──────────────────────────────────────────────────────┐
│                    MEMPALACE                          │
│                                                      │
│  ┌─── Room: auth ──┐  ┌─── Room: pipeline ──┐       │
│  │ Hall: facts      │  │ Hall: decisions     │       │
│  │ Hall: procedures │  │ Hall: events        │       │
│  │ Hall: warnings   │  │ Hall: facts         │       │
│  │                  │  │                     │       │
│  │  L0 ████ always  │  │  L0 ████ always     │       │
│  │  L1 ███░ warm    │  │  L1 ███░ warm       │       │
│  │  L2 ██░░ cold    │  │  L2 ██░░ cold       │       │
│  │  L3 █░░░ archive │  │  L3 █░░░ archive    │       │
│  └──────────────────┘  └─────────────────────┘       │
│           │                      │                   │
│           └──── Tunnel ──────────┘                   │
│                (cross-bank bridge)                   │
│                                                      │
│  Closets: compressed summaries + source pointers     │
└──────────────────────┬───────────────────────────────┘
                       │
              Hindsight vector store
              (embeddings + semantic search)
```

**Rooms** — topic isolation. Auth, pipeline, infrastructure, schema — each topic in its own room. An agent searching for auth facts won't wade through 500 deploy memories.

**Halls** — knowledge typing within a room. Fact, event, decision, procedure, warning. The system knows *what* it's looking at before reading — like `Content-Type` for memory.

**Layers L0–L3** — four priority tiers. L0 (core) is always loaded. L3 (archive) is deep-search only. Same idea as CPU cache hierarchy: L1 is fast and small, RAM is slow but holds everything.

**Closets** — AI-compressed summaries with source pointers. Deduplication at the knowledge level: 10 related facts → 1 paragraph + references.

**Tunnels** — cross-bank bridges between agents. Agent A discovers an insight — Agent B sees it through a tunnel without data duplication.

## Comparison

| | [Hindsight](https://github.com/vectorize-io/hindsight) | [MemPalace](https://github.com/milla-jovovich/mempalace) | **This fork** |
|---|---|---|---|
| **What it is** | Long-term memory store | Hierarchical taxonomy spec | Storage + taxonomy hybrid |
| **Storage** | Vector store + embeddings | None (spec only) | Vector store + embeddings |
| **Memory structure** | Flat (all memories equal) | Rooms → Halls → Layers | Rooms → Halls → Layers + embeddings |
| **Retrieval** | Semantic search | No retrieval engine | Room-scoped semantic search |
| **Classification** | None | Defined in spec | Keyword-based, <1ms, zero LLM cost |
| **Priority tiers** | All memories equal | L0–L3 (spec) | L0–L3 (implemented) |
| **Compression** | None | Closets (spec) | Closets with source pointers |
| **Multi-agent** | Shared bank | Tunnels (spec) | Tunnels (cross-bank bridges) |
| **MCP integration** | API only | None | **5 tools via MCP protocol** |
| **Setup** | Docker | Manual config | Docker (drop-in upgrade) |

## Quick start

```bash
git clone https://github.com/holetron/hindsight-mempalace.git
cd hindsight-mempalace
cp .env.example .env
# edit .env with your config
docker compose -f docker-compose.mempalace.yml up -d
```

API available at `http://localhost:5100`. Drop-in replacement for vanilla Hindsight — same API, same clients, new brain.

### Embeddings

Ships with `BAAI/bge-small-en-v1.5` (384-dim) — fast, CPU-friendly, baked into the image so first run needs no network download. It's **English-optimized**; recall quality on other languages degrades.

For multilingual memory (e.g. RU, multi-script), point it at a multilingual model:

```bash
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3   # 1024-dim, multilingual
```

Dimension is detected automatically. ⚠️ Switching models changes the vector dimension — do it on an **empty** memory store, or wipe + re-embed, since existing vectors can't be mixed across dimensions.

## MCP Server

The `mcp-server/` directory contains a standalone [MCP](https://modelcontextprotocol.io) server. Any MCP-compatible client (Claude Code, OpenClaw, Cursor, etc.) connects and gets structured long-term memory.

### Tools

| Tool | Description |
|------|-------------|
| `memory_retain` | Save a memory with automatic room/hall classification |
| `memory_recall` | Scoped semantic search with room/hall/layer filters |
| `memory_reflect` | Deep reasoning — synthesize facts, find patterns, answer with citations |
| `memory_compress` | Create closet summaries from accumulated facts |
| `memory_bridge` | Cross-bank tunnels between related memories |

### Setup

```bash
cd mcp-server
npm install
HINDSIGHT_URL=http://localhost:5100 node server.js
```

### Claude Code config

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

See [`mcp-server/README.md`](./mcp-server/README.md) for full docs and environment variables.

## API changes from upstream

The base `/retain` and `/recall` endpoints are fully backward-compatible. New parameters are optional.

### New parameters

| Endpoint | Parameter | Type | Description |
|----------|-----------|------|-------------|
| `/retain` | `room` | string | Topic room (auto-classified if omitted) |
| `/retain` | `hall` | string | Knowledge type (auto-classified if omitted) |
| `/retain` | `layer` | int | Priority 0-3 (default: 2) |
| `/recall` | `room` | string | Filter recall to a specific room |
| `/recall` | `hall` | string | Filter recall to a specific hall |
| `/recall` | `max_layer` | int | Maximum layer depth to search |

### New endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/bridge` | Create a cross-bank memory bridge |
| GET | `/tunnels` | List existing tunnels |
| POST | `/tunnels` | Create a tunnel between banks |
| GET | `/closets` | List compressed memory summaries |
| POST | `/closets` | Compress L3 memories into a closet |

## Room/Hall taxonomy

### Rooms (topics)

`auth` · `pipeline` · `infrastructure` · `deployment` · `schema` · `api` · `ui` · `tax` · `hr` · `legal` · `compliance` · `monitoring` · `agent` · `general`

### Halls (knowledge types)

`warning` · `decision` · `procedure` · `event` · `preference` · `discovery` · `fact`

### Layers

| Layer | Name | Behavior |
|-------|------|----------|
| **L0** | Critical | Always recalled |
| **L1** | Important | Recalled by default |
| **L2** | Normal | Standard (default for new memories) |
| **L3** | Archive | Deep search only, compressed into closets |

## Auto-classification

MemPalace includes a keyword-based classifier (`room_hall_classifier.py`) that assigns room and hall automatically when not provided. No LLM call — classification is instant and free.

Extensible: add keywords to `ROOM_KEYWORDS` / `HALL_KEYWORDS` dictionaries.

## Examples

### Store a memory

```bash
curl -X POST http://localhost:5100/retain \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "project-alpha",
    "text": "Never restart PROD PM2 without confirming DEV works first.",
    "room": "deployment",
    "hall": "warning",
    "layer": 0
  }'
```

### Scoped recall

```bash
curl -X POST http://localhost:5100/recall \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "project-alpha",
    "query": "deployment safety rules",
    "room": "deployment",
    "hall": "warning",
    "max_layer": 1
  }'
```

### Cross-bank bridge

```bash
curl -X POST http://localhost:5100/bridge \
  -H "Content-Type: application/json" \
  -d '{
    "source_bank": "project-alpha",
    "target_bank": "project-beta",
    "room": "infrastructure",
    "hall": "procedure"
  }'
```

## What we changed

A taxonomy layer over Hindsight's vector store, plus a standalone MCP server.

Key additions:
- `room_hall_classifier.py` — keyword-based taxonomy engine (new)
- `aa1_add_room_hall_to_memory_units.py` — DB migration: flat → hierarchical, adds room/hall + `layer` column (new)
- `mcp-server/` — standalone MCP server with 5 tools (new)
- Storage layer — room/hall/layer metadata on every write
- Retrieval — room-scoped search with hall filtering
- Compression — closet generation with source linking
- Tunnels — cross-bank memory sharing protocol

Full architectural spec: [MEMPALACE.md](./MEMPALACE.md)

## Upstream compatibility

This fork tracks `vectorize-io/hindsight` as upstream. To pull updates:

```bash
git remote add upstream https://github.com/vectorize-io/hindsight.git
git fetch upstream
git merge upstream/main
```

All changes are additive — existing Hindsight behavior is preserved.

## Credits

- [**Hindsight**](https://github.com/vectorize-io/hindsight) by vectorize-io — the memory storage engine
- [**MemPalace**](https://github.com/milla-jovovich/mempalace) by milla-jovovich — the hierarchical taxonomy architecture
- [Holetron](https://github.com/holetron) — fork maintainers, MCP server, integration

## License

MIT — same as upstream Hindsight. See [LICENSE](./LICENSE).
