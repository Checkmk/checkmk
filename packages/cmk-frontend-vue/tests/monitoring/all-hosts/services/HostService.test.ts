/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { visibleHostFields } from '@/monitoring/all-hosts/columns'
import { HostService } from '@/monitoring/all-hosts/services/HostService'
import type { HostEntry, HostsResponse } from '@/monitoring/shared/api/types'
import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'

import { makeKeyShortcutService } from '../../shared/services/testHelpers'

function makeHostsResponse(hosts: HostEntry[], matched: number, total: number): HostsResponse {
  return { hosts, meta: { limit: 1000, matched, total, fields: [] } }
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
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=host-1',
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

  it('calls api.fetchHosts on construction and populates items/counts', async () => {
    const host = makeHost()
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([host], 1, 10))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenCalledTimes(1)
    expect(service.items.value).toEqual([host])
    expect(service.matched.value).toBe(1)
    expect(service.total.value).toBe(10)
    expect(service.fetchState.value).toBe('idle')
  })

  it('passes sort state to api.fetchHosts after updateSort is called', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    service.updateSort([{ id: 'name', desc: false }])
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenLastCalledWith(
      {
        limit: DEFAULT_BATCH_SIZE,
        sort: [{ id: 'name', desc: false }],
        searchQuery: '',
        fields: visibleHostFields({})
      },
      expect.any(AbortSignal)
    )
  })

  it('passes the search query to api.fetchHosts after updateSearch is called', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    service.updateSearch('web01')
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenLastCalledWith(
      {
        limit: DEFAULT_BATCH_SIZE,
        sort: [],
        searchQuery: 'web01',
        fields: visibleHostFields({})
      },
      expect.any(AbortSignal)
    )
  })

  it('a background poll does not pick up search text typed but never submitted', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)
    service.updateSearch('web01')
    await vi.advanceTimersByTimeAsync(0)

    // Mirrors the live v-model binding: typing without pressing Enter.
    service.searchQuery.value = 'web01x'

    service.refresh()
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenLastCalledWith(
      {
        limit: DEFAULT_BATCH_SIZE,
        sort: [],
        searchQuery: 'web01',
        fields: visibleHostFields({})
      },
      expect.any(AbortSignal)
    )
  })

  describe('requested fields', () => {
    const COLUMNS = [{ accessorKey: 'address', header: 'IP address' }] as const

    function makeService(fetchHosts: () => Promise<HostsResponse>): HostService {
      return new HostService({ fetchHosts }, makeKeyShortcutService(), { columns: [...COLUMNS] })
    }

    it('leaves a hidden column out of the next request', async () => {
      const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
      service = makeService(fetchHosts)
      await vi.advanceTimersByTimeAsync(0)

      service.updateColumnVisibility({ address: false })
      service.updateSearch('web01')
      await vi.advanceTimersByTimeAsync(0)

      expect(fetchHosts).toHaveBeenLastCalledWith(
        expect.objectContaining({ fields: visibleHostFields({ address: false }) }),
        expect.any(AbortSignal)
      )
    })

    it('fetches the field of a column that is shown again', async () => {
      const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
      service = makeService(fetchHosts)
      await vi.advanceTimersByTimeAsync(0)
      service.updateColumnVisibility({ address: false })
      await vi.advanceTimersByTimeAsync(0)
      expect(fetchHosts).toHaveBeenCalledTimes(1)

      service.updateColumnVisibility({})
      await vi.advanceTimersByTimeAsync(0)

      expect(fetchHosts).toHaveBeenCalledTimes(2)
      expect(fetchHosts).toHaveBeenLastCalledWith(
        expect.objectContaining({ fields: visibleHostFields({}) }),
        expect.any(AbortSignal)
      )
    })
  })

  it('offers the configured limits and starts at the smallest one', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService(), {
      limitTiers: [1000, 5000]
    })

    await vi.advanceTimersByTimeAsync(0)

    expect(service.offeredLimits).toEqual([1000, 5000])
    expect(service.requestedLimit.value).toBe(1000)
    expect(fetchHosts).toHaveBeenLastCalledWith(
      expect.objectContaining({ limit: 1000 }),
      expect.any(AbortSignal)
    )
  })

  it('appends an unlimited limit when the user may remove the limit', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService(), {
      limitTiers: [1000, 5000],
      mayRemoveLimit: true
    })

    await vi.advanceTimersByTimeAsync(0)

    expect(service.offeredLimits).toEqual([1000, 5000, null])
  })

  it('does not offer an unlimited limit when the user may not remove the limit', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService(), {
      limitTiers: [1000, 5000],
      mayRemoveLimit: false
    })

    await vi.advanceTimersByTimeAsync(0)

    expect(service.offeredLimits).toEqual([1000, 5000])
  })

  it('refetches with the chosen limit when it is changed', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService(), {
      limitTiers: [1000, 5000]
    })

    await vi.advanceTimersByTimeAsync(0)

    service.setRequestedLimit(5000)
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchHosts).toHaveBeenLastCalledWith(
      expect.objectContaining({ limit: 5000 }),
      expect.any(AbortSignal)
    )

    service.setRequestedLimit(1000)
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchHosts).toHaveBeenLastCalledWith(
      expect.objectContaining({ limit: 1000 }),
      expect.any(AbortSignal)
    )
  })

  it('pauses the auto-refresh while the limit is unlimited and resumes when it is bounded again', async () => {
    const fetchHosts = vi.fn().mockResolvedValue(makeHostsResponse([], 0, 0))
    service = new HostService({ fetchHosts }, makeKeyShortcutService(), {
      limitTiers: [1000, 5000],
      mayRemoveLimit: true
    })

    await vi.advanceTimersByTimeAsync(0)
    expect(service.paused.value).toBe(false)

    service.setRequestedLimit(null)
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchHosts).toHaveBeenLastCalledWith(
      expect.objectContaining({ limit: null }),
      expect.any(AbortSignal)
    )
    expect(service.paused.value).toBe(true)

    service.setRequestedLimit(1000)
    await vi.advanceTimersByTimeAsync(0)
    expect(service.paused.value).toBe(false)
  })
})
