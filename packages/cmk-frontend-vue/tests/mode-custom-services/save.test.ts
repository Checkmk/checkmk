/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Black-box behaviour of the persistence path: drive createCustomService with a model,
// stub the create endpoint at the network boundary (MSW) and assert only the observable
// outcome (created / error surfaced / guarded).
import { CmkApiError } from 'cmk-ui-library/lib/error'
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
const CREATE_URL = `${API_BASE}/domain-types/custom_service/collections/all`

let createRequests = 0
let lastBody: unknown = null

function completeModel() {
  return {
    ...emptyService(),
    metricName: 'otel.http.duration',
    serviceName: 'HTTP duration',
    hostName: 'web01'
  }
}

const server = setupServer(
  http.post(CREATE_URL, async ({ request }) => {
    createRequests += 1
    lastBody = await request.json()
    return HttpResponse.json({
      domainType: 'custom_service',
      id: 'http_duration',
      title: 'HTTP duration'
    })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  createRequests = 0
  lastBody = null
  server.resetHandlers()
})
afterAll(() => server.close())

describe('createCustomService', () => {
  test('persists the service and reports success', async () => {
    const result = await createCustomService(completeModel())
    expect(result.ok).toBe(true)
    expect(createRequests).toBe(1)
  })

  test('sends the payload the endpoint expects', async () => {
    await createCustomService(completeModel())
    expect(lastBody).toEqual({
      configuration_name: 'http_duration',
      host_assignment: { mode: 'explicit_host', host_name: 'web01' },
      configuration: {
        metric_name: 'otel.http.duration',
        service_name_template: 'HTTP duration',
        consolidation: { type: 'gauge_last' },
        consolidation_lookback: 120
      }
    })
  })

  test('surfaces the backend error message when the name is already taken', async () => {
    server.use(
      http.post(CREATE_URL, () =>
        HttpResponse.json(
          {
            status: 409,
            title: 'Custom service already exists',
            detail: 'A configuration named "http_duration" already exists.'
          },
          { status: 409 }
        )
      )
    )
    const result = await createCustomService(completeModel())
    expect(result.ok).toBe(false)
    expect(result.error).toContain('already exists')
  })

  test('lets a server fault through so it keeps its crash report', async () => {
    server.use(
      http.post(CREATE_URL, () =>
        HttpResponse.json(
          { status: 500, title: 'Internal Server Error', detail: 'boom' },
          { status: 500 }
        )
      )
    )
    await expect(createCustomService(completeModel())).rejects.toThrow(CmkApiError)
  })

  test('refuses to save with an incomplete consolidation and issues no request', async () => {
    const result = await createCustomService({
      ...completeModel(),
      consolidation: {
        type: 'histogram',
        function: 'histogram_fraction_between',
        lookback_seconds: 120,
        percentile: 90,
        lower_threshold: 10
      }
    })
    expect(result.ok).toBe(false)
    expect(result.error).toBeTruthy()
    expect(createRequests).toBe(0)
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
    expect(result.error).toBeTruthy()
    expect(createRequests).toBe(0)
  })
})
