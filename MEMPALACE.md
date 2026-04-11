# MemPalace Architecture

> Hierarchical memory system extending Hindsight. Based on ADR-145 design spec.

## Overview

MemPalace adds spatial organization to Hindsight's flat memory bank. Every memory unit gets classified into a **Room** (topic) and **Hall** (knowledge type), assigned a **Layer** (priority 0-3), and optionally linked via **Tunnels** (cross-bank bridges) or compressed into **Closets** (summaries).

The result is a navigable, priority-aware memory structure that replaces flat vector search with structured recall — without breaking any existing Hindsight behavior.

## Core Concepts

### Rooms (Topics)

Rooms represent topical areas. Each memory is classified into exactly one room.

| Room | Description |
|---|---|
| `auth` | Authentication, authorization, tokens, sessions |
| `pipeline` | CI/CD, build pipelines, automation chains |
| `infrastructure` | Servers, networking, hardware, OS-level config |
| `deployment` | Deploy procedures, rollbacks, release management |
| `schema` | Database schema, migrations, data models |
| `api` | API endpoints, contracts, integrations |
| `ui` | Frontend, components, layout, styling |
| `tax` | Tax calculations, fiscal rules, reporting |
| `hr` | Human resources, hiring, onboarding |
| `legal` | Legal requirements, contracts, terms |
| `compliance` | Regulatory compliance, audits, certifications |
| `monitoring` | Logs, alerts, metrics, observability |
| `agent` | AI agents, tools, prompts, agent behavior |
| `general` | Fallback for unclassified memories |

### Halls (Knowledge Types)

Halls categorize the nature of knowledge. Each memory belongs to exactly one hall.

| Hall | Description |
|---|---|
| `warning` | Things to avoid, dangers, prohibitions |
| `decision` | Choices made, approvals, rejections |
| `procedure` | How-to, step-by-step processes |
| `event` | Things that happened — incidents, releases, milestones |
| `preference` | Likes, favorites, style choices |
| `discovery` | Findings, insights, research results |
| `fact` | General factual statements (default) |

### Layers (Priority L0-L3)

Layers control recall priority. Lower number = higher priority.

| Layer | Name | Behavior | Example |
|---|---|---|---|
| **L0** | Critical | Must always be recalled | "Never delete production DB" |
| **L1** | Important | High relevance, recalled by default | "Deploy requires DEV test first" |
| **L2** | Normal | Standard facts (default for new memories) | "API uses JWT auth" |
| **L3** | Archive | Low priority, only recalled when specifically requested | "Old endpoint deprecated in v2" |

### Tunnels (Cross-Bank Bridges)

Tunnels connect memory units across different banks, enabling cross-context recall. A tunnel is a directed link between two memory units in separate banks, with optional metadata describing the relationship.

Use cases:
- A deployment procedure in one bank linked to an incident report in another
- A schema decision linked to the API change it motivated
- A warning in a project bank linked to the same warning in a team bank

Tunnels are bidirectional by default — creating a tunnel from A to B also makes B discoverable from A.

### Closets (Compressed Summaries)

Closets are AI-generated summaries of groups of related memories. They reduce noise in recall by consolidating repetitive or related facts into a single summary unit.

Each closet stores:
- The compressed summary text
- A vector embedding for search
- References to the source memory units it was built from
- The room and hall inherited from the source group

Closets are created on demand (via API) or automatically when a room exceeds a configurable memory count threshold.

## Database Schema Changes

### Modified: `memory_units` table

Added columns:

```sql
ALTER TABLE memory_units ADD COLUMN room VARCHAR(64) DEFAULT 'general';
ALTER TABLE memory_units ADD COLUMN hall VARCHAR(64) DEFAULT 'fact';
ALTER TABLE memory_units ADD COLUMN layer INTEGER DEFAULT 2;
```

### New table: `tunnels`

Stores cross-bank links with metadata.

```sql
CREATE TABLE tunnels (
    id UUID PRIMARY KEY,
    source_unit_id UUID REFERENCES memory_units(id),
    target_unit_id UUID REFERENCES memory_units(id),
    source_bank_id UUID REFERENCES memory_banks(id),
    target_bank_id UUID REFERENCES memory_banks(id),
    relationship VARCHAR(256),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### New table: `closets`

Stores compressed summaries with embeddings.

```sql
CREATE TABLE closets (
    id UUID PRIMARY KEY,
    bank_id UUID REFERENCES memory_banks(id),
    room VARCHAR(64),
    hall VARCHAR(64),
    summary TEXT NOT NULL,
    embedding VECTOR(1536),
    source_unit_ids UUID[],
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Migration

File: `aa1_add_room_hall_to_memory_units.py`

Applies all three schema changes (columns + tables) in a single migration. Existing memory units get default values (`room='general'`, `hall='fact'`, `layer=2`).

## Auto-Classification

The `room_hall_classifier.py` module classifies memories using keyword regex patterns. No LLM call is needed — this keeps classification fast and deterministic.

**Algorithm:**
1. Run memory text against `ROOM_PATTERNS` — first match wins, set room
2. Run memory text against `HALL_PATTERNS` — first match wins, set hall
3. If no match: fall back to `room="general"`, `hall="fact"`

**To extend classification:** add patterns to `ROOM_PATTERNS` or `HALL_PATTERNS` lists in `room_hall_classifier.py`. Patterns are evaluated in order, so place more specific patterns before general ones.

## API Extensions

### Retain — `POST /banks/{bank_id}/retain`

New optional fields in request body:

| Field | Type | Default | Description |
|---|---|---|---|
| `room` | string | auto-classified | Override auto-classification for room |
| `hall` | string | auto-classified | Override auto-classification for hall |
| `layer` | integer | `2` | Priority level 0-3 |

If `room` or `hall` are omitted, the auto-classifier assigns them. If provided, the explicit value takes precedence.

### Recall — `GET /banks/{bank_id}/recall`

New optional query parameters:

| Param | Type | Default | Description |
|---|---|---|---|
| `room` | string | — | Filter results by room |
| `hall` | string | — | Filter results by hall |
| `max_layer` | integer | — | Only return memories with layer <= this value |

These filters are applied after vector search, narrowing results from the ranked candidates.

### New Endpoints

#### `POST /bridge`
Create a cross-bank memory bridge (convenience wrapper around tunnels).

#### `GET /tunnels`
List all tunnels, optionally filtered by bank.

#### `POST /tunnels`
Create a tunnel linking two memory units across banks.

Request body:
```json
{
    "source_unit_id": "uuid",
    "target_unit_id": "uuid",
    "relationship": "optional description"
}
```

#### `GET /closets`
List closets, optionally filtered by bank, room, or hall.

#### `POST /closets`
Create a closet (AI-compressed summary) from a set of memory units.

Request body:
```json
{
    "bank_id": "uuid",
    "source_unit_ids": ["uuid", "uuid"],
    "room": "optional",
    "hall": "optional"
}
```

The summary is generated by the AI and stored with a vector embedding for future recall.

## Files Modified

11 files modified from upstream, 2 new files added. See `README.md` for the full list.

Key files:
- `room_hall_classifier.py` — auto-classification logic (new)
- `aa1_add_room_hall_to_memory_units.py` — database migration (new)
- Retain/recall endpoints — extended with room/hall/layer support
- Tunnel and closet endpoints — new route handlers

## Design Principles

1. **Additive-only changes** — upstream Hindsight compatibility is fully preserved. No existing behavior is altered; all new fields are optional.
2. **No LLM calls for classification** — keyword heuristics keep classification fast, cheap, and deterministic. LLM is only used for closet summary generation.
3. **Optional parameters** — all new fields default to sensible values. Existing API consumers work unchanged without modification.
4. **Extensible taxonomy** — rooms and halls are soft-coded via pattern lists in the classifier, not hardcoded enums. Adding a new room or hall is a one-line pattern addition.
