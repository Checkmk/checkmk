/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readFileSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const allComponents = JSON.parse(
  readFileSync(
    path.join(path.dirname(fileURLToPath(import.meta.url)), '../../ucl-components.json'),
    'utf8'
  )
)

const CATALOG = allComponents.map(({ name, slug, category, publicUrl }) => ({
  name,
  slug,
  category,
  publicUrl
}))
const COMPONENTS = Object.fromEntries(allComponents.map((c) => [c.slug, c]))

const TOOLS = [
  {
    name: 'list_components',
    description:
      'Returns the full UCL component catalog. Each entry includes name, slug, category, and importPath.',
    inputSchema: { type: 'object', properties: {} }
  },
  {
    name: 'get_component',
    description:
      'Returns full details for a single UCL component: props (name/type/default/options), codeExample, and accessibility data.',
    inputSchema: {
      type: 'object',
      properties: {
        slug: { type: 'string', description: "Component slug, e.g. 'cmkbutton' or 'cmkinput'" }
      },
      required: ['slug'],
      additionalProperties: false
    }
  },
  {
    name: 'search_components',
    description: 'Filter the UCL component catalog by name and/or category.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Partial name or slug to search for' },
        category: {
          type: 'string',
          description: 'Optional category slug to restrict results (e.g. "basic-elements")'
        }
      },
      required: ['query'],
      additionalProperties: false
    }
  }
]

const send = (msg) => process.stdout.write(JSON.stringify(msg) + '\n')

function dispatch({ jsonrpc = '2.0', id, method, params }) {
  if (method === 'initialize') {
    send({
      jsonrpc,
      id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'ucl', version: '1.0.0' }
      }
    })
    return
  }
  if (id == null) return // notification — no response

  if (method === 'tools/list') {
    send({ jsonrpc, id, result: { tools: TOOLS } })
    return
  }

  if (method === 'tools/call') {
    const name = params?.name
    const args = params?.arguments ?? {}
    let data

    if (name === 'list_components') {
      data = CATALOG
    } else if (name === 'get_component') {
      data = COMPONENTS[args.slug]
      if (!data) {
        send({ jsonrpc, id, error: { code: -32602, message: `Unknown component: ${args.slug}` } })
        return
      }
    } else if (name === 'search_components') {
      const q = (args.query ?? '').toLowerCase()
      data = CATALOG.filter((c) => c.name.toLowerCase().includes(q) || c.slug.includes(q))
      if (args.category)
        data = data.filter((c) => c.category.toLowerCase() === args.category.toLowerCase())
    } else {
      send({ jsonrpc, id, error: { code: -32601, message: `Unknown tool: ${name}` } })
      return
    }

    send({ jsonrpc, id, result: { content: [{ type: 'text', text: JSON.stringify(data) }] } })
    return
  }

  send({ jsonrpc, id, error: { code: -32601, message: `Method not found: ${method}` } })
}

// ── MCP JSON-RPC stdio transport ────────────────────────────────────────
process.stdin.setEncoding('utf8')
let _buf = ''
process.stdin.on('data', (d) => {
  _buf += d
  const lines = _buf.split('\n')
  _buf = lines.pop() ?? ''
  for (const line of lines) {
    if (line.trim()) {
      try {
        dispatch(JSON.parse(line))
      } catch {
        /* ignore malformed */
      }
    }
  }
})
