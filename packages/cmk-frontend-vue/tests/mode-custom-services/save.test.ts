/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Black-box behaviour of the persistence path: drive createCustomService and
// updateCustomService with a model, stub the endpoints at the network boundary (MSW) and
// assert only the observable outcome (written / error surfaced / guarded).
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, test } from 'vitest'

import { createCustomService, updateCustomService } from '@/mode-custom-services/save'
import { emptyService } from '@/mode-custom-services/types'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const CREATE_URL = `${API_BASE}/domain-types/custom_service/collections/all`
const OBJECT_URL = `${API_BASE}/objects/custom_service/http_duration_on_web01`

let createRequests = 0
let updateRequests = 0
let lastBody: unknown = null
let lastIfMatch: string | null = null

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
  }),
  http.put(OBJECT_URL, async ({ request }) => {
    updateRequests += 1
    lastBody = await request.json()
    lastIfMatch = request.headers.get('If-Match')
    return HttpResponse.json({
      domainType: 'custom_service',
      id: 'http_duration_on_web01',
      title: 'HTTP duration'
    })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  createRequests = 0
  updateRequests = 0
  lastBody = null
  lastIfMatch = null
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
      configuration_name: 'http_duration_on_web01',
      host_assignment: { mode: 'explicit_host', host_name: 'web01' },
      configuration: {
        metric_name: 'otel.http.duration',
        service_name_template: 'HTTP duration',
        consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 120 }
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
        lower_threshold: 10
      } as ConsolidationFunction
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

describe('updateCustomService', () => {
  test('writes the service and reports success', async () => {
    const result = await updateCustomService('http_duration_on_web01', completeModel(), 'etag-1')
    expect(result.ok).toBe(true)
    expect(updateRequests).toBe(1)
  })

  test('sends what create sends, without the configuration name', async () => {
    await updateCustomService('http_duration_on_web01', completeModel(), 'etag-1')
    expect(lastBody).toEqual({
      host_assignment: { mode: 'explicit_host', host_name: 'web01' },
      configuration: {
        metric_name: 'otel.http.duration',
        service_name_template: 'HTTP duration',
        consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 120 }
      }
    })
  })

  test('sends back the etag it was given, so a concurrent change is detected', async () => {
    await updateCustomService('http_duration_on_web01', completeModel(), 'etag-1')
    expect(lastIfMatch).toBe('etag-1')
  })

  test('surfaces the backend error message when the etag is stale', async () => {
    server.use(
      http.put(OBJECT_URL, () =>
        HttpResponse.json(
          {
            status: 412,
            title: 'Precondition failed',
            detail: 'The custom service has changed in the meantime.'
          },
          { status: 412 }
        )
      )
    )
    const result = await updateCustomService('http_duration_on_web01', completeModel(), 'stale')
    expect(result.ok).toBe(false)
    expect(result.error).toContain('changed in the meantime')
  })

  test('refuses to write without a host and issues no request', async () => {
    const result = await updateCustomService(
      'http_duration_on_web01',
      { ...completeModel(), hostName: null },
      'etag-1'
    )
    expect(result.ok).toBe(false)
    expect(result.error).toBeTruthy()
    expect(updateRequests).toBe(0)
  })
})
