/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HostService } from '@/monitoring/all-hosts/services/HostService'
import type { HostEntry } from '@/monitoring/shared/api/types'

import { makeResponse } from '../../shared/services/testHelpers'

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'host-1',
    state: 'UP',
    ip: '10.0.0.1',
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
    const fetchHosts = vi.fn().mockResolvedValue(makeResponse([host], 1))
    service = new HostService({ fetchHosts })

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchHosts).toHaveBeenCalledTimes(1)
    expect(service.items.value).toEqual([host])
    expect(service.total.value).toBe(1)
    expect(service.loading.value).toBe(false)
  })
})
