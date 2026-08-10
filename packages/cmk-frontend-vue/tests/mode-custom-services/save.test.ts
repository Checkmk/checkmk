/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Black-box behaviour of the persistence path: drive createCustomService with a
// model, stub the config-entity REST API at the network boundary (MSW) and assert
// only the observable outcome (created / error surfaced / guarded). Nothing here
// depends on how save.ts builds the payload, so it survives internal refactors.
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, test, vi } from 'vitest'

import { createCustomService } from '@/mode-custom-services/save'
import { emptyService } from '@/mode-custom-services/types'

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

const API_BASE = `${location.protocol}//${location.host}/api/internal`

let createRequests = 0

function completeModel() {
  return {
    ...emptyService(),
    metricName: 'otel.http.duration',
    serviceName: 'HTTP duration',
    hostName: 'web01'
  }
}

const server = setupServer(
  // Rule catalog defaults the wizard starts from.
  http.get(`${API_BASE}/domain-types/form_spec/collections/:entityType`, () =>
    HttpResponse.json({
      extensions: {
        schema: {},
        default_values: { value: {}, conditions: { type: ['explicit', {}] } }
      }
    })
  ),
  // Successful rule creation by default; individual tests override for failures.
  http.post(`${API_BASE}/domain-types/configuration_entity/collections/all`, () => {
    createRequests += 1
    return HttpResponse.json({ id: 'rule-1', title: 'HTTP duration' })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  createRequests = 0
  server.resetHandlers()
})
afterAll(() => server.close())

describe('createCustomService', () => {
  test('persists the service and reports success', async () => {
    const result = await createCustomService(completeModel())
    expect(result.ok).toBe(true)
    expect(createRequests).toBe(1)
  })

  test('surfaces the backend error message when creation is rejected', async () => {
    server.use(
      http.post(`${API_BASE}/domain-types/configuration_entity/collections/all`, () =>
        HttpResponse.json(
          {
            status: 422,
            title: 'Validation failed',
            detail: 'invalid',
            ext: { validation_errors: [{ message: 'Host does not exist' }] }
          },
          { status: 422 }
        )
      )
    )
    const result = await createCustomService(completeModel())
    expect(result.ok).toBe(false)
    expect(result.error).toContain('Host does not exist')
  })

  test('refuses to save without a host and issues no request', async () => {
    const result = await createCustomService({ ...completeModel(), hostName: null })
    expect(result.ok).toBe(false)
    expect(result.error).toBeTruthy()
    expect(createRequests).toBe(0)
  })

  test('refuses to save without a metric and issues no request', async () => {
    const result = await createCustomService({ ...completeModel(), metricName: null })
    expect(result.ok).toBe(false)
    expect(createRequests).toBe(0)
  })
})
