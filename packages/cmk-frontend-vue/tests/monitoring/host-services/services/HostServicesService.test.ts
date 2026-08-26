/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HostServicesService } from '@/monitoring/host-services/services/HostServicesService'
import type { HostRef, HostServiceEntry, HostServicesResponse } from '@/monitoring/shared/api/types'
import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'

import { makeKeyShortcutService } from '../../shared/services/testHelpers'

const HOST: HostRef = { name: 'web-1', site_id: 'local' }

function makeServicesResponse(
  services: HostServiceEntry[],
  matched: number,
  total: number
): HostServicesResponse {
  return {
    services,
    meta: { hostname: HOST.name, site_id: HOST.site_id, limit: DEFAULT_BATCH_SIZE, matched, total }
  }
}

function makeService(overrides: Partial<HostServiceEntry> = {}): HostServiceEntry {
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

describe('HostServicesService', () => {
  let service: HostServicesService | null = null

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    service?.stopPolling()
    service = null
    vi.useRealTimers()
  })

  it('calls api.fetchServices on construction and populates items/counts', async () => {
    const entry = makeService()
    const fetchServices = vi.fn().mockResolvedValue(makeServicesResponse([entry], 1, 10))
    service = new HostServicesService({ fetchServices }, HOST, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchServices).toHaveBeenCalledTimes(1)
    expect(service.items.value).toEqual([entry])
    expect(service.matched.value).toBe(1)
    expect(service.total.value).toBe(10)
    expect(service.fetchState.value).toBe('idle')
  })

  it('requests the services of the host it was built for', async () => {
    const fetchServices = vi.fn().mockResolvedValue(makeServicesResponse([], 0, 0))
    service = new HostServicesService({ fetchServices }, HOST, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchServices).toHaveBeenLastCalledWith(
      HOST,
      {
        limit: DEFAULT_BATCH_SIZE,
        sort: [],
        searchQuery: '',
        filter: undefined,
        fields: ['labels', 'tags', 'contacts', 'contact_groups']
      },
      expect.any(AbortSignal)
    )
  })

  it('passes sort state to api.fetchServices after updateSort is called', async () => {
    const fetchServices = vi.fn().mockResolvedValue(makeServicesResponse([], 0, 0))
    service = new HostServicesService({ fetchServices }, HOST, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    service.updateSort([{ id: 'state', desc: true }])
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchServices).toHaveBeenLastCalledWith(
      { ...HOST },
      {
        limit: DEFAULT_BATCH_SIZE,
        sort: [{ id: 'state', desc: true }],
        searchQuery: '',
        filter: undefined,
        fields: ['labels', 'tags', 'contacts', 'contact_groups']
      },
      expect.any(AbortSignal)
    )
  })

  it('passes the search query to api.fetchServices after updateSearch is called', async () => {
    const fetchServices = vi.fn().mockResolvedValue(makeServicesResponse([], 0, 0))
    service = new HostServicesService({ fetchServices }, HOST, makeKeyShortcutService())

    await vi.advanceTimersByTimeAsync(0)

    service.updateSearch('CPU')
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchServices).toHaveBeenLastCalledWith(
      { ...HOST },
      {
        limit: DEFAULT_BATCH_SIZE,
        sort: [],
        searchQuery: 'CPU',
        filter: undefined,
        fields: ['labels', 'tags', 'contacts', 'contact_groups']
      },
      expect.any(AbortSignal)
    )
  })
})
