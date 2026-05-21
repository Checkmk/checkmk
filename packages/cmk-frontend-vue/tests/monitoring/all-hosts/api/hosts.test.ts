/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import { HostApi } from '@/monitoring/all-hosts/api/hosts'
import type { HostEntry, HostsPageMeta, HostsResponse } from '@/monitoring/shared/api/types'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('@/lib/rest-api-client/client', () => ({
  default: { GET: mockGet },
  unwrap: vi.fn((result: { data?: unknown; error?: unknown }) => {
    if (result.error !== undefined) {
      throw new Error('api error')
    }
    return result.data
  })
}))

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
  it('calls GET monitor/hosts without query params when called with no arguments', async () => {
    const response = makeHostsResponse([makeHost()])
    mockGet.mockResolvedValueOnce({ data: response, response: new Response() })

    const result = await new HostApi().fetchHosts()

    expect(mockGet).toHaveBeenCalledWith('monitor/hosts', { params: {} })
    expect(result).toEqual(response)
  })

  it('passes query params when provided', async () => {
    const response = makeHostsResponse([])
    mockGet.mockResolvedValueOnce({ data: response, response: new Response() })

    await new HostApi().fetchHosts({ limit: '50' })

    expect(mockGet).toHaveBeenCalledWith('monitor/hosts', { params: { query: { limit: '50' } } })
  })

  it('returns the response data from the API', async () => {
    const hosts = [makeHost({ name: 'db-1', state: 'DOWN' }), makeHost({ name: 'web-1' })]
    const response = makeHostsResponse(hosts)
    mockGet.mockResolvedValueOnce({ data: response, response: new Response() })

    const result = await new HostApi().fetchHosts()

    expect(result).toEqual(response)
  })
})
