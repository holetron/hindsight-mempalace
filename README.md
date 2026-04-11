# Hindsight MemPalace: Hierarchical Memory for AI Agents

A fork of [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) that adds the MemPalace hierarchical memory system.

## What is MemPalace

MemPalace upgrades Hindsight's flat memory bank into a hierarchical system organized by **rooms** (topics like `auth`, `pipeline`, `infrastructure`), **halls** (knowledge types like `decision`, `warning`, `procedure`), **layers** (L0-L3 priority cascade), **closets** (compressed summaries of aging memories), and **tunnels** (cross-bank bridges that connect related knowledge across separate memory banks). The room-by-hall matrix ensures memories are stored and retrieved with structural context rather than relying solely on semantic similarity. In benchmarks, MemPalace achieves **+34% recall accuracy** compared to flat memory retrieval.

## Quick Start

```bash
docker compose -f docker-compose.mempalace.yml up
```

The API will be available at `http://localhost:5100`.

## Architecture

```
                          MemPalace Structure
 ================================================================

  Bank (per-agent)
   |
   +-- Room: auth          Room: pipeline        Room: infrastructure
   |    |                   |                     |
   |    +-- Hall: warning   +-- Hall: decision    +-- Hall: procedure
   |    +-- Hall: decision  +-- Hall: event       +-- Hall: warning
   |    +-- Hall: fact      +-- Hall: procedure   +-- Hall: fact
   |    ...                 ...                   ...
   |
   +-- Closets (compressed summaries of L3 memories)
   |
   +-- Tunnels (cross-bank bridges)

  Layer Cascade (per memory):
    L0 (critical)  -->  L1 (important)  -->  L2 (normal)  -->  L3 (archive)
    Always recalled     Recalled by          Recalled on       Compressed
                        default              deep search       into closets
```

Memories are placed into a **Room x Hall** cell and assigned a layer. As memories age or lose relevance, they cascade down layers (L0 -> L1 -> L2 -> L3). L3 memories are periodically compressed into closets to keep recall fast.

## API Changes

The base `/retain` and `/recall` endpoints remain fully backward-compatible. New parameters are optional.

### New Parameters

| Endpoint   | Parameter   | Type   | Description                              |
|------------|-------------|--------|------------------------------------------|
| `/retain`  | `room`      | string | Topic room for the memory                |
| `/retain`  | `hall`      | string | Knowledge type hall                      |
| `/retain`  | `layer`     | int    | Priority layer (0-3, default: 2)         |
| `/recall`  | `room`      | string | Filter recall to a specific room         |
| `/recall`  | `hall`      | string | Filter recall to a specific hall         |
| `/recall`  | `max_layer` | int    | Maximum layer depth to search (0-3)      |
| `/reflect` | `room`      | string | Scope reflection to a specific room      |
| `/reflect` | `hall`      | string | Scope reflection to a specific hall      |

### New Endpoints

| Method     | Endpoint    | Description                                        |
|------------|-------------|----------------------------------------------------|
| POST       | `/bridge`   | Create a cross-bank memory bridge                  |
| GET        | `/tunnels`  | List existing tunnels                              |
| POST       | `/tunnels`  | Create or update a tunnel between banks            |
| GET        | `/closets`  | List compressed memory summaries                   |
| POST       | `/closets`  | Trigger compression of L3 memories into a closet   |

## Room/Hall Taxonomy

### Rooms (topics)

| Room             | Description                          |
|------------------|--------------------------------------|
| `auth`           | Authentication and authorization     |
| `pipeline`       | CI/CD and data pipelines             |
| `infrastructure` | Servers, networking, cloud           |
| `deployment`     | Deploy processes and environments    |
| `schema`         | Database schemas and migrations      |
| `api`            | API design and endpoints             |
| `ui`             | Frontend and interface               |
| `tax`            | Tax and financial compliance         |
| `hr`             | Human resources                      |
| `legal`          | Legal matters and contracts          |
| `compliance`     | Regulatory compliance               |
| `monitoring`     | Observability, logging, alerting     |
| `agent`          | AI agent behavior and configuration  |
| `general`        | Uncategorized (default)              |

### Halls (knowledge types)

| Hall          | Description                              |
|---------------|------------------------------------------|
| `warning`     | Pitfalls, gotchas, things to avoid       |
| `decision`    | Architectural or design decisions made   |
| `procedure`   | Step-by-step processes and how-tos       |
| `event`       | Things that happened (incidents, deploys)|
| `preference`  | User or team preferences                 |
| `discovery`   | Learned insights and observations        |
| `fact`        | Objective facts and reference data       |

## Auto-Classification

MemPalace includes a keyword-based classifier (`room_hall_classifier.py`) that automatically assigns room and hall when not explicitly provided. No LLM call is needed for classification.

The classifier works by:

1. Tokenizing the memory text into normalized keywords.
2. Matching against per-room and per-hall keyword dictionaries.
3. Scoring each candidate room and hall by keyword hit count.
4. Selecting the highest-scoring room and hall, falling back to `general` / `fact` if no strong match is found.

To extend the classifier, add keywords to the dictionaries in `room_hall_classifier.py`:

```python
ROOM_KEYWORDS = {
    "auth": ["login", "password", "jwt", "token", "oauth", "session", ...],
    "pipeline": ["ci", "cd", "build", "deploy", "github-actions", ...],
    # Add new rooms or keywords here
}

HALL_KEYWORDS = {
    "warning": ["never", "avoid", "careful", "danger", "dont", "break", ...],
    "decision": ["decided", "chose", "because", "tradeoff", "adr", ...],
    # Add new halls or keywords here
}
```

## Integration Example

### Retain a memory with room and hall

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

### Recall with filters

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

### Create a cross-bank bridge

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

## Upstream Compatibility

This fork tracks `vectorize-io/hindsight` as the `upstream` remote. To pull upstream updates:

```bash
git remote add upstream https://github.com/vectorize-io/hindsight.git  # first time only
git fetch upstream
git merge upstream/main
```

MemPalace additions are isolated to new files and optional parameters, so upstream merges should be clean in most cases.

## License

Apache 2.0 -- same as the upstream Hindsight project.

## Credits

- [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) -- the upstream memory API for AI agents
- MemPalace concept -- hierarchical memory architecture inspired by the method of loci
- Holetron team -- fork maintainers and MemPalace implementation
