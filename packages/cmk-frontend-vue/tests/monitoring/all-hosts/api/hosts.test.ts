/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import client from '@/lib/rest-api-client/client'

import { HostApi } from '@/monitoring/all-hosts/api/hosts'
import type { HostEntry, HostsPageMeta, HostsResponse } from '@/monitoring/shared/api/types'
import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'host-1',
    state: 'UP',
    address: '10.0.0.1',
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
  return { hosts, meta: { limit: DEFAULT_BATCH_SIZE, total: hosts.length, ...meta } }
}

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

describe('HostApi.fetchHosts', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockSuccess(body: unknown): void {
    postSpy.mockResolvedValueOnce({
      data: body as HostsResponse,
      error: undefined,
      response: new Response()
    } as never)
  }

  it('calls the hosts endpoint with no query params when called with no arguments', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts()

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE }
    })
  })

  it('includes limit param when provided', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ limit: 50 })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', { ...CONTENT_TYPE, body: { limit: 50 } })
  })

  it('serializes sort entries as column:direction strings', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({
      sort: [
        { id: 'name', desc: false },
        { id: 'state', desc: true }
      ]
    })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE, sort: ['name:asc', 'state:desc'] }
    })
  })

  it('serializes a single ascending sort entry', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ sort: [{ id: 'alias', desc: false }] })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE, sort: ['alias:asc'] }
    })
  })

  it('serializes a single descending sort entry', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ sort: [{ id: 'num_services', desc: true }] })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE, sort: ['num_services:desc'] }
    })
  })

  it('omits sort params when sort array is empty', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ sort: [] })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE }
    })
  })

  it('omits sort params when sort is not provided', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({})

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE }
    })
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(new HostApi().fetchHosts()).rejects.toThrow()
  })

  it('forwards a non-empty search query as the q param', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ searchQuery: 'web-server' })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE, q: 'web-server' }
    })
  })

  it('omits the q param when the search query is empty', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ searchQuery: '' })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE }
    })
  })

  it('omits the q param when the search query is only whitespace', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ searchQuery: '   ' })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE }
    })
  })

  it('keeps other params when omitting an empty q', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ limit: 50, searchQuery: '' })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: 50 }
    })
  })

  it('returns the response data from the API', async () => {
    const hosts = [makeHost({ name: 'db-1', state: 'DOWN' }), makeHost({ name: 'web-1' })]
    const response = makeHostsResponse(hosts)
    mockSuccess(response)

    const result = await new HostApi().fetchHosts()

    expect(result).toEqual(response)
  })
})
