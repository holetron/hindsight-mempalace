#!/usr/bin/env node

/**
 * Hindsight MemPalace — Standalone MCP Server
 *
 * Provides 5 memory tools over MCP (stdio transport):
 *   memory_retain   — save memories with room/hall/layer classification
 *   memory_recall   — scoped semantic search
 *   memory_reflect  — deep reasoning over stored memories
 *   memory_compress — create closet summaries
 *   memory_bridge   — cross-bank tunnels
 *
 * Connects to Hindsight API (default: http://127.0.0.1:5100)
 *
 * Usage:
 *   HINDSIGHT_URL=http://localhost:5100 node server.js
 *
 * Claude Code config (~/.claude/mcp.json):
 *   {
 *     "mcpServers": {
 *       "mempalace": {
 *         "command": "node",
 *         "args": ["/path/to/mcp-server/server.js"],
 *         "env": { "HINDSIGHT_URL": "http://localhost:5100" }
 *       }
 *     }
 *   }
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

// --- Config ---

const HINDSIGHT_URL = process.env.HINDSIGHT_URL || 'http://127.0.0.1:5100';
const HINDSIGHT_BASE = `${HINDSIGHT_URL}/v1/default/banks`;
const DEFAULT_BANK = process.env.MEMPALACE_BANK || 'mempalace-main';

// --- Hindsight HTTP client ---

async function hindsightRequest(method, path, body = null) {
  const url = `${HINDSIGHT_BASE}${path}`;
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(url, opts);
  const text = await res.text();

  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Hindsight returned non-JSON: ${text.slice(0, 200)}`);
  }

  if (!res.ok) {
    throw new Error(data.detail || `Hindsight API error ${res.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

// --- MCP Server ---

const server = new McpServer({
  name: 'hindsight-mempalace',
  version: '1.0.0',
});

// Tool 1: memory_retain
server.tool(
  'memory_retain',
  'Save a fact, observation, or document to long-term memory with automatic room/hall classification. ' +
  'Rooms: auth, pipeline, schema, infrastructure, ui, api, deployment, monitoring, agent, general. ' +
  'Halls: fact, event, decision, preference, discovery, procedure, warning. ' +
  'Layers: L0=Identity (always loaded), L1=Critical, L2=Session (default), L3=Deep.',
  {
    text: z.string().describe('The text to memorize — a fact, observation, or document content'),
    bank_id: z.string().optional().describe(`Memory bank ID (default: ${DEFAULT_BANK})`),
    context: z.string().optional().describe('Context label (e.g. "meeting notes", "client call")'),
    document_id: z.string().optional().describe('Document ID to group related facts'),
    tags: z.array(z.string()).optional().describe('Tags for categorization'),
    room: z.string().optional().describe('Topic room (auto-classified if omitted)'),
    hall: z.enum(['fact', 'event', 'decision', 'preference', 'discovery', 'procedure', 'warning']).optional().describe('Knowledge type (auto-classified if omitted)'),
    layer: z.enum(['L0', 'L1', 'L2', 'L3']).optional().describe('Priority layer (default: L2)'),
  },
  async ({ text, bank_id, context, document_id, tags, room, hall, layer }) => {
    const bankId = bank_id || DEFAULT_BANK;
    const item = { content: text };
    if (context) item.context = context;
    if (document_id) item.document_id = document_id;
    if (tags) item.tags = tags;
    if (room) item.room = room;
    if (hall) item.hall = hall;
    if (layer) item.layer = layer;

    const result = await hindsightRequest('POST', `/${bankId}/memories`, {
      items: [item],
    });

    const storedIds = (result.items || []).map(i => i.id || i.uuid).filter(Boolean);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          bank_id: bankId,
          items_stored: result.items_count || 1,
          ids: storedIds.length ? storedIds : null,
          room: room || 'auto',
          hall: hall || 'auto',
          layer: layer || 'L2',
        }, null, 2),
      }],
    };
  }
);

// Tool 2: memory_recall
server.tool(
  'memory_recall',
  'Search long-term memory for relevant facts. Uses semantic search with optional room/hall scoping ' +
  'for significantly improved retrieval accuracy. Supports layer cascade (L0 results always prioritized).',
  {
    query: z.string().describe('What to search for in memory'),
    bank_id: z.string().optional().describe(`Memory bank ID (default: ${DEFAULT_BANK})`),
    limit: z.number().optional().describe('Max results (default: 10)'),
    room: z.union([z.string(), z.array(z.string())]).optional().describe('Filter by room(s) — applied before semantic search'),
    hall: z.union([z.string(), z.array(z.string())]).optional().describe('Filter by hall(s): fact, event, decision, etc.'),
    max_layer: z.enum(['L0', 'L1', 'L2', 'L3']).optional().describe('Max layer depth to search (default: L3 = all)'),
  },
  async ({ query, bank_id, limit, room, hall, max_layer }) => {
    const bankId = bank_id || DEFAULT_BANK;

    const body = {
      query,
      limit: limit || 10,
    };
    if (room) body.room = Array.isArray(room) ? room : [room];
    if (hall) body.hall = Array.isArray(hall) ? hall : [hall];
    if (max_layer) body.max_layer = max_layer;

    const result = await hindsightRequest('POST', `/${bankId}/memories/recall`, body);

    const memories = (result.results || []).map(r => ({
      id: r.id || r.uuid || null,
      text: r.text,
      type: r.type,
      entities: r.entities,
      occurred: r.occurred_start || null,
      room: r.room || null,
      hall: r.hall || null,
    }));

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          bank_id: bankId,
          count: memories.length,
          memories,
        }, null, 2),
      }],
    };
  }
);

// Tool 3: memory_reflect
server.tool(
  'memory_reflect',
  'Deep reasoning over memory — synthesizes facts, finds patterns, answers complex questions with citations. ' +
  'Use for analysis: "What patterns emerge from recent events?" or "Summarize everything about X."',
  {
    query: z.string().describe('Question to reason about over stored memories'),
    bank_id: z.string().optional().describe(`Memory bank ID (default: ${DEFAULT_BANK})`),
  },
  async ({ query, bank_id }) => {
    const bankId = bank_id || DEFAULT_BANK;

    const result = await hindsightRequest('POST', `/${bankId}/reflect`, { query });

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          bank_id: bankId,
          answer: result.answer || result.response || result.text || JSON.stringify(result),
          citations: result.based_on || result.citations || [],
        }, null, 2),
      }],
    };
  }
);

// Tool 4: memory_compress
server.tool(
  'memory_compress',
  'Create compressed memory summaries (closets) from stored facts. Groups memories by room+hall ' +
  'and creates AI-generated summaries with source pointers. Use when a topic has accumulated many facts.',
  {
    bank_id: z.string().optional().describe(`Memory bank ID (default: ${DEFAULT_BANK})`),
    room: z.string().optional().describe('Topic to compress (e.g. "auth", "pipeline")'),
    hall: z.string().optional().describe('Knowledge type to compress (e.g. "fact", "decision")'),
    min_sources: z.number().optional().describe('Min memories needed to create a closet (default: 5)'),
    query: z.string().optional().describe('Query to guide compression focus'),
  },
  async ({ bank_id, room, hall, min_sources, query }) => {
    const bankId = bank_id || DEFAULT_BANK;

    const body = {};
    if (room) body.room = room;
    if (hall) body.hall = hall;
    if (min_sources) body.min_sources = min_sources;
    if (query) body.query = query;

    const result = await hindsightRequest('POST', `/${bankId}/closets`, body);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          bank_id: bankId,
          closets_created: result.closets_created || 0,
          closets: result.closets || [],
        }, null, 2),
      }],
    };
  }
);

// Tool 5: memory_bridge
server.tool(
  'memory_bridge',
  'Create a cross-bank memory bridge (tunnel) between two related memories in different banks. ' +
  'Relations: same_concept, depends_on, contradicts, extends. Use when concepts in separate banks are related.',
  {
    source_bank: z.string().describe('Source bank ID'),
    source_memory: z.string().describe('UUID of the source memory'),
    target_bank: z.string().describe('Target bank ID'),
    target_memory: z.string().describe('UUID of the target memory'),
    relation: z.enum(['same_concept', 'depends_on', 'contradicts', 'extends']).describe('Relationship type'),
    confidence: z.number().min(0).max(1).optional().describe('Confidence score 0.0–1.0 (default: 0.8)'),
  },
  async ({ source_bank, source_memory, target_bank, target_memory, relation, confidence }) => {
    const body = {
      source_bank,
      source_memory,
      target_bank,
      target_memory,
      relation,
    };
    if (confidence !== undefined) body.confidence = confidence;

    const result = await hindsightRequest('POST', `/${source_bank}/tunnels`, body);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          tunnel: result.tunnel || result,
        }, null, 2),
      }],
    };
  }
);

// --- Resources ---

server.resource(
  'memory-config',
  'mempalace://config',
  async () => ({
    contents: [{
      uri: 'mempalace://config',
      mimeType: 'application/json',
      text: JSON.stringify({
        hindsight_url: HINDSIGHT_URL,
        default_bank: DEFAULT_BANK,
        rooms: ['auth', 'pipeline', 'schema', 'infrastructure', 'ui', 'api', 'deployment', 'monitoring', 'agent', 'general'],
        halls: ['fact', 'event', 'decision', 'preference', 'discovery', 'procedure', 'warning'],
        layers: {
          L0: 'Identity — always loaded',
          L1: 'Critical facts — per-space',
          L2: 'Session context — per-conversation (default)',
          L3: 'Deep memory — full search only',
        },
      }, null, 2),
    }],
  })
);

// --- Start ---

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`hindsight-mempalace-mcp running (Hindsight: ${HINDSIGHT_URL}, bank: ${DEFAULT_BANK})`);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
