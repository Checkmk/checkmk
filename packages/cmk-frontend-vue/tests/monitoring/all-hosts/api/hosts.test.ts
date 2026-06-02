/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import client from '@/lib/rest-api-client/client'

import { HostApi } from '@/monitoring/all-hosts/api/hosts'
import type { HostEntry, HostsPageMeta, HostsResponse } from '@/monitoring/shared/api/types'

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'host-1',
    state: 'UP',
    ip: '10.0.0.1',
    alias: 'host 1',
    site_id: 'local',
    num_services: 1,
    num_services_ok: 1,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    ...overrides
  }
}

function makeHostsResponse(hosts: HostEntry[], meta: Partial<HostsPageMeta> = {}): HostsResponse {
  return { hosts, meta: { limit: 1000, total: hosts.length, ...meta } }
}

describe('HostApi.fetchHosts', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let getSpy: any

  beforeEach(() => {
    getSpy = vi.spyOn(client, 'GET')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockSuccess(body: unknown): void {
    getSpy.mockResolvedValueOnce({
      data: body as HostsResponse,
      error: undefined,
      response: new Response()
    } as never)
  }

  it('calls the hosts endpoint with no query params when called with no arguments', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts()

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', { params: { query: {} } })
  })

  it('includes limit param when provided', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ limit: 50 })

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', {
      params: { query: { limit: '50' } }
    })
  })

  it('serializes sort entries as repeated sort params', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({
      sort: [
        { id: 'name', desc: false },
        { id: 'state', desc: true }
      ]
    })

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', {
      params: { query: { sort: ['name:asc', 'state:desc'] } }
    })
  })

  it('serializes a single ascending sort entry', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ sort: [{ id: 'alias', desc: false }] })

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', {
      params: { query: { sort: ['alias:asc'] } }
    })
  })

  it('serializes a single descending sort entry', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ sort: [{ id: 'num_services', desc: true }] })

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', {
      params: { query: { sort: ['num_services:desc'] } }
    })
  })

  it('omits sort params when sort array is empty', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ sort: [] })

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', { params: { query: {} } })
  })

  it('omits sort params when sort is not provided', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({})

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts', { params: { query: {} } })
  })

  it('throws when the response is not ok', async () => {
    getSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(new HostApi().fetchHosts()).rejects.toThrow()
  })

  it('returns the response data from the API', async () => {
    const hosts = [makeHost({ name: 'db-1', state: 'DOWN' }), makeHost({ name: 'web-1' })]
    const response = makeHostsResponse(hosts)
    mockSuccess(response)

    const result = await new HostApi().fetchHosts()

    expect(result).toEqual(response)
  })
})
