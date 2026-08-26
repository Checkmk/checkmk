/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HostServicesApi } from '@/monitoring/host-services/api/services'
import type { HostRef } from '@/monitoring/shared/api/types'

type ApiServiceEntry = components['schemas']['HostServiceEntry']

const HOST: HostRef = { name: 'web-1', site_id: 'local' }

function makeApiEntry(overrides: Partial<ApiServiceEntry> = {}): ApiServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    is_flapping: false,
    stale: false,
    summary: 'OK - 15 min load: 0.5',
    last_check: 1783942710,
    last_state_change: 1783942740,
    ...overrides
  }
}

const EXPECTED_PARAMS = {
  params: {
    path: { hostname: 'web-1' },
    query: { site_id: 'local' },
    header: { 'Content-Type': 'application/json' }
  }
}

describe('HostServicesApi.fetchServices', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockSuccess(services: ApiServiceEntry[]): void {
    postSpy.mockResolvedValueOnce({
      data: {
        services,
        meta: {
          hostname: 'web-1',
          site_id: 'local',
          limit: 1000,
          matched: services.length,
          total: services.length
        }
      },
      error: undefined,
      response: new Response()
    } as never)
  }

  it('calls the host services endpoint with the host, site and default limit', async () => {
    mockSuccess([])

    await new HostServicesApi().fetchServices(HOST)

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000 }
    })
  })

  it('sends the requested limit', async () => {
    mockSuccess([])

    await new HostServicesApi().fetchServices(HOST, { limit: 25 })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 25 }
    })
  })

  it('encodes the sort state as column:direction values', async () => {
    mockSuccess([])

    await new HostServicesApi().fetchServices(HOST, {
      sort: [
        { id: 'state', desc: true },
        { id: 'name', desc: false }
      ]
    })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000, sort: ['state:desc', 'name:asc'] }
    })
  })

  it('sends the trimmed search query as q', async () => {
    mockSuccess([])

    await new HostServicesApi().fetchServices(HOST, { searchQuery: '  CPU  ' })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000, q: 'CPU' }
    })
  })

  it('omits q when the search query is blank', async () => {
    mockSuccess([])

    await new HostServicesApi().fetchServices(HOST, { searchQuery: '   ' })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000 }
    })
  })

  it('omits the sort key when nothing is sorted', async () => {
    mockSuccess([])

    await new HostServicesApi().fetchServices(HOST, { sort: [] })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000 }
    })
  })

  it('forwards an abort signal when provided', async () => {
    mockSuccess([])
    const signal = new AbortController().signal

    await new HostServicesApi().fetchServices(HOST, {}, signal)

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000 },
      signal
    })
  })

  it('returns the services reported by the endpoint', async () => {
    const entry = makeApiEntry()
    mockSuccess([entry])

    const response = await new HostServicesApi().fetchServices(HOST)

    expect(response.services).toEqual([entry])
  })

  it('carries the matched and total counts from the page meta', async () => {
    postSpy.mockResolvedValueOnce({
      data: {
        services: [makeApiEntry()],
        meta: { hostname: 'web-1', site_id: 'local', limit: 1000, matched: 7, total: 42 }
      },
      error: undefined,
      response: new Response()
    } as never)

    const response = await new HostServicesApi().fetchServices(HOST)

    expect(response.meta.matched).toBe(7)
    expect(response.meta.total).toBe(42)
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 404, statusText: 'Not Found' })
    } as never)

    await expect(new HostServicesApi().fetchServices(HOST)).rejects.toThrow()
  })
})
