/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HostService } from '@/monitoring/all-hosts/services/HostService'
import type { HostEntry, HostsResponse } from '@/monitoring/shared/api/types'

import { makeKeyShortcutService } from '../../shared/services/testHelpers'

function makeHostsResponse(hosts: HostEntry[], total: number): HostsResponse {
  return { hosts, meta: { limit: 1000, total } }
}

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'host-1',
    state: 'UP',
    address: '10.0.0.1',
    alias: 'host 1',
    site_id: 'local',
    num_services: 0,
    num_services_ok: 0,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    ...overrides
  }
}

describe('HostService', () => {
  let service: HostService | null = null

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    service?.stopPolling()
    service = null
    vi.useRealTimers()
  })

  it('calls api.fetchHosts on construction and populates items/total', async () => {
    const host = makeHost()
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([host], 1))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenCalledTimes(1)
    expect(service.items.value).toEqual([host])
    expect(service.total.value).toBe(1)
    expect(service.loading.value).toBe(false)
  })

  it('passes sort state to api.fetchHosts after updateSort is called', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    service.updateSort([{ id: 'name', desc: false }])
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenLastCalledWith({
      sort: [{ id: 'name', desc: false }],
      searchQuery: ''
    })
  })

  it('passes the search query to api.fetchHosts after updateSearch is called', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    service.updateSearch('web01')
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenLastCalledWith({ sort: [], searchQuery: 'web01' })
  })
})
