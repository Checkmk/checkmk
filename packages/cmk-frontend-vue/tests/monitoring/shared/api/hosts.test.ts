/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HostApi } from '@/monitoring/shared/api/hosts'
import type {
  FilterNode,
  HostEntry,
  HostsPageMeta,
  HostsRequestBody,
  HostsResponse
} from '@/monitoring/shared/api/types'
import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'

const NOW = 1789625643

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'host-1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    address: '10.0.0.1',
    alias: 'host 1',
    site_id: 'local',
    num_services: 1,
    num_services_ok: 1,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=host-1',
    num_relations: 0,
    ...overrides
  }
}

function makeHostsResponse(hosts: HostEntry[], meta: Partial<HostsPageMeta> = {}): HostsResponse {
  return {
    hosts,
    meta: {
      limit: DEFAULT_BATCH_SIZE,
      matched: hosts.length,
      total: hosts.length,
      fields: [],
      ...meta
    }
  }
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
    vi.useRealTimers()
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

  it('forwards a null limit to request no limit at all', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ limit: null })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: null }
    })
  })

  it('asks for the given optional fields only', async () => {
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({ fields: ['address', 'num_services'] })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE, fields: ['address', 'num_services'] }
    })
  })

  it('asks for no optional field at all when the list is empty', async () => {
    mockSuccess(makeHostsResponse([]))

    // Distinct from omitting `fields`, which leaves the API to its default set.
    await new HostApi().fetchHosts({ fields: [] })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: { limit: DEFAULT_BATCH_SIZE, fields: [] }
    })
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

  it('sends an age filter as the absolute bound it resolves to', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW * 1000)
    mockSuccess(makeHostsResponse([]))

    await new HostApi().fetchHosts({
      filter: { type: 'age', field: 'last_check', op: 'older_than', seconds: 300 }
    })

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts', {
      ...CONTENT_TYPE,
      body: {
        limit: DEFAULT_BATCH_SIZE,
        filter: { type: 'condition', field: 'last_check', op: 'lte', value: NOW - 300 }
      }
    })
  })

  it('resolves an age filter anew on every request', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW * 1000)
    const api = new HostApi()
    const filter: FilterNode = {
      type: 'age',
      field: 'last_check',
      op: 'younger_than',
      seconds: 300
    }

    mockSuccess(makeHostsResponse([]))
    await api.fetchHosts({ filter })
    vi.setSystemTime((NOW + 60) * 1000)
    mockSuccess(makeHostsResponse([]))
    await api.fetchHosts({ filter })

    expect(
      postSpy.mock.calls.map(
        (call: unknown[]) => (call[1] as { body: HostsRequestBody }).body.filter
      )
    ).toEqual([
      { type: 'condition', field: 'last_check', op: 'gte', value: NOW - 300 },
      { type: 'condition', field: 'last_check', op: 'gte', value: NOW + 60 - 300 }
    ])
  })

  it('returns the response data from the API', async () => {
    const hosts = [makeHost({ name: 'db-1', state: 'DOWN' }), makeHost({ name: 'web-1' })]
    const response = makeHostsResponse(hosts)
    mockSuccess(response)

    const result = await new HostApi().fetchHosts()

    expect(result).toEqual(response)
  })
})
