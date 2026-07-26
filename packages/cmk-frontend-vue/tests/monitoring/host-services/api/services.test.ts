/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HostServicesApi } from '@/monitoring/host-services/api/services'

type ApiServiceEntry = components['schemas']['HostServiceEntry']

function makeApiEntry(overrides: Partial<ApiServiceEntry> = {}): ApiServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    summary: 'OK - 15 min load: 0.5',
    last_check: '2026-07-13T11:38:30Z',
    last_state_change: '2026-07-13T11:39:00Z',
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

    await new HostServicesApi().fetchServices('web-1', 'local')

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000 }
    })
  })

  it('forwards an abort signal when provided', async () => {
    mockSuccess([])
    const signal = new AbortController().signal

    await new HostServicesApi().fetchServices('web-1', 'local', signal)

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/services', {
      ...EXPECTED_PARAMS,
      body: { limit: 1000 },
      signal
    })
  })

  it('maps each entry to a ServiceEntry view model', async () => {
    mockSuccess([makeApiEntry({ name: 'CPU load', state: 'OK' })])

    const result = await new HostServicesApi().fetchServices('web-1', 'local')

    expect(result).toEqual([
      {
        name: 'CPU load',
        state: 'OK',
        summary: 'OK - 15 min load: 0.5',
        last_check: '2026-07-13T11:38:30Z',
        last_state_change: '2026-07-13T11:39:00Z'
      }
    ])
  })

  it('normalizes the UNKN state label to the shared UNKNOWN state', async () => {
    mockSuccess([makeApiEntry({ state: 'UNKN' })])

    const [entry] = await new HostServicesApi().fetchServices('web-1', 'local')

    expect(entry!.state).toBe('UNKNOWN')
  })

  it.each([
    ['OK', 'OK'],
    ['WARN', 'WARN'],
    ['CRIT', 'CRIT']
  ] as const)('passes the %s state through unchanged', async (label, expected) => {
    mockSuccess([makeApiEntry({ state: label })])

    const [entry] = await new HostServicesApi().fetchServices('web-1', 'local')

    expect(entry!.state).toBe(expected)
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 404, statusText: 'Not Found' })
    } as never)

    await expect(new HostServicesApi().fetchServices('web-1', 'local')).rejects.toThrow()
  })
})
