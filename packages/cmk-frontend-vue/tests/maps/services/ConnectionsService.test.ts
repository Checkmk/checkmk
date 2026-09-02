/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'

import { ConnectionsApi } from '@/maps/api/connections'
import { createMapsDaemonClient } from '@/maps/api/transport'
import { ConnectionsService } from '@/maps/services/ConnectionsService'
import type { ConnectionConfig } from '@/maps/types/api'

// The daemon boundary is simulated with msw, so the real transport runs: URL
// building and error mapping are exercised rather than a hand-written fake.

const sampleConnection: ConnectionConfig = {
  id: 'live_1',
  type: 'livestatus',
  label: 'Live 1',
  socket_path: '/tmp/live',
  host: null,
  port: 6557,
  timeout: 10,
  tls: false,
  tls_verify: true,
  checkmk_url: null,
  automation_user: null,
  automation_secret: null
}

const server = setupServer(
  http.get('*/api/v1/connections', () => HttpResponse.json([sampleConnection]))
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function newService(): ConnectionsService {
  return new ConnectionsService(
    new ConnectionsApi(createMapsDaemonClient({ headers: () => undefined }))
  )
}

describe('ConnectionsService', () => {
  it('starts with no connections', () => {
    expect(newService().connections.value).toEqual([])
  })

  it('populates the connections on success', async () => {
    const service = newService()
    await service.fetch()
    expect(service.connections.value).toEqual([sampleConnection])
    expect(service.error.value).toBeNull()
  })

  it('reports the daemon error message on failure', async () => {
    server.use(
      http.get('*/api/v1/connections', () =>
        HttpResponse.json({ detail: 'Failed' }, { status: 500 })
      )
    )
    const service = newService()
    await service.fetch()
    expect(service.error.value).toBe('Failed')
  })

  it('resolves the display label, falling back to the id', async () => {
    const service = newService()
    await service.fetch()
    expect(service.labelFor('live_1')).toBe('Live 1')
    expect(service.labelFor('unknown')).toBe('unknown')
  })

  it('shares one request between concurrent lazy loads', async () => {
    let requests = 0
    server.use(
      http.get('*/api/v1/connections', () => {
        requests += 1
        return HttpResponse.json([sampleConnection])
      })
    )
    const service = newService()
    await Promise.all([service.ensureLoaded(), service.ensureLoaded()])
    expect(requests).toBe(1)
    // Already loaded: no further request.
    await service.ensureLoaded()
    expect(requests).toBe(1)
  })
})
