/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'

import {
  MAX_MATCHES,
  searchCustomServices,
  suggestServiceNames
} from '@/mode-alerts/service-client'

// The default client singleton captures `globalThis.fetch` at import time, before
// server.listen() patches it. Re-create it with a lazy fetch wrapper so MSW can intercept.
vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const mod = await importOriginal<Record<string, unknown>>()
  const createClientImpl = (await import('openapi-fetch')).default
  return {
    ...mod,
    default: createClientImpl({
      baseUrl: `${location.protocol}//${location.host}/api/internal`,
      credentials: 'include',
      headers: { Accept: 'application/json' },
      fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args)
    })
  }
})

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/service/collections/all`

interface Condition {
  op: string
  left: string
  right: string
}

interface RequestBody {
  columns: string[]
  sites: string[]
  query: { op: string; expr: Condition[] }
}

let sentBody: RequestBody | null = null
let matching: Array<[string, string]> = []

function entries(): Array<{ extensions: { host_name: string; description: string } }> {
  return matching.map(([hostName, serviceName]) => ({
    extensions: { host_name: hostName, description: serviceName }
  }))
}

const server = setupServer(
  http.post(ENDPOINT, async ({ request }) => {
    sentBody = (await request.json()) as RequestBody
    return HttpResponse.json({ id: 'all', links: [], value: entries() })
  })
)

function conditionOn(field: string): Condition | undefined {
  return sentBody?.query.expr.find((condition) => condition.left === field)
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  sentBody = null
  matching = []
  server.resetHandlers()
})
afterAll(() => server.close())

test('an exact match asks livestatus for string equality on the service name', async () => {
  await searchCustomServices('exact', 'HTTP request duration')

  expect(conditionOn('description')).toEqual({
    op: '=',
    left: 'description',
    right: 'HTTP request duration'
  })
})

test('a regex match asks livestatus for a regex match on the service name', async () => {
  await searchCustomServices('regex', 'HTTP.*duration')

  expect(conditionOn('description')).toEqual({
    op: '~',
    left: 'description',
    right: 'HTTP.*duration'
  })
})

test('the search is restricted to services of the custom services check plugin', async () => {
  await searchCustomServices('exact', 'HTTP request duration')

  expect(conditionOn('check_command')).toEqual({
    op: '=',
    left: 'check_command',
    right: 'check_mk-telemetry_metrics_custom_query'
  })
})

test('only the host and service name columns are requested', async () => {
  await searchCustomServices('exact', 'HTTP request duration')

  expect(sentBody?.columns).toEqual(['host_name', 'description'])
})

test('a matched service is reported with its host and service name', async () => {
  matching = [['web01', 'HTTP request duration']]

  expect(await searchCustomServices('exact', 'HTTP request duration')).toEqual({
    services: [{ hostName: 'web01', serviceName: 'HTTP request duration' }],
    truncated: false
  })
})

test('a response without a collection yields no services', async () => {
  server.use(http.post(ENDPOINT, () => HttpResponse.json({ id: 'all', links: [] })))

  expect(await searchCustomServices('exact', 'HTTP request duration')).toEqual({
    services: [],
    truncated: false
  })
})

test('a match set beyond the limit is capped and reported as truncated', async () => {
  matching = Array.from({ length: MAX_MATCHES + 1 }, (_, index) => [
    `web${index}`,
    'HTTP request duration'
  ])

  const result = await searchCustomServices('regex', 'HTTP')

  expect(result.services).toHaveLength(MAX_MATCHES)
  expect(result.truncated).toBe(true)
})

test('a rejected query is raised as an API error carrying the status', async () => {
  server.use(
    http.post(ENDPOINT, () =>
      HttpResponse.json(
        { title: 'Bad Request', detail: 'Invalid regular expression' },
        { status: 400 }
      )
    )
  )

  await expect(searchCustomServices('regex', '[')).rejects.toSatisfy(
    (error: unknown) => error instanceof CmkApiError && error.statusCode === 400
  )
})

test('suggestions are searched for, so a partially typed name still finds candidates', async () => {
  await suggestServiceNames('exact', 'HTTP')

  expect(conditionOn('description')).toEqual({ op: '~', left: 'description', right: 'HTTP' })
})

test('an exact match escapes the query so it is searched for literally', async () => {
  await suggestServiceNames('exact', 'duration (p95)')

  expect(conditionOn('description')?.right).toBe('duration \\(p95\\)')
})

test('a regular expression is searched for as written', async () => {
  await suggestServiceNames('regex', 'HTTP.*duration')

  expect(conditionOn('description')?.right).toBe('HTTP.*duration')
})

test('a service name shared by several hosts is suggested once', async () => {
  matching = [
    ['web01', 'HTTP request duration'],
    ['web02', 'HTTP request duration'],
    ['db01', 'Query duration']
  ]

  expect(await suggestServiceNames('regex', 'duration')).toEqual({
    names: ['HTTP request duration', 'Query duration'],
    truncated: false
  })
})
