/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearDataBindingCache,
  useDataBinding
} from '@/maps/map/presentation/composables/useDataBinding'

import { fakeMapsServices, runWithServices } from '../../../support/services'

let services: ReturnType<typeof fakeMapsServices>

describe('useDataBinding', () => {
  beforeEach(() => {
    services = fakeMapsServices()
    clearDataBindingCache()
  })

  it('caches BI aggregation lookups per connection', async () => {
    vi.mocked(services.apis.objects.fetchAggregations).mockResolvedValue([
      { id: 'aggr1', title: 'Web shop', pack_id: 'default', function: 'worst' }
    ])
    const b = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect((await b.aggregations())[0]!.title).toBe('Web shop')
    await b.aggregations()
    expect(vi.mocked(services.apis.objects.fetchAggregations)).toHaveBeenCalledTimes(1)

    const other = runWithServices(services, () => useDataBinding(() => 'live_2'))
    await other.aggregations()
    expect(vi.mocked(services.apis.objects.fetchAggregations)).toHaveBeenCalledTimes(2)
  })

  it('caches metrics per host/service', async () => {
    // The daemon ships the raw perfdata source; titles come from the GUI
    // metric-info resolution (fetchMetricChoices merges the two).
    vi.mocked(services.apis.objects.fetchPerfMetrics).mockResolvedValue({
      perf_data: 'load1=2.5;;;; load5=1.5;;;;',
      check_command: 'check_mk-cpu_loads',
      metrics: ['load1', 'load5']
    })
    vi.mocked(services.apis.metricInfo.resolve).mockResolvedValue({
      perfometer: null,
      metrics: {
        load1: {
          name: 'load1',
          title: 'CPU load average of last minute',
          scale: 1,
          color: '#15d1a0',
          unit: { notation: 'decimal', symbol: '', precision: { type: 'auto', digits: 2 } }
        }
      }
    })
    const b = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await b.metrics('web01', 'CPU load')).toEqual([
      { name: 'load1', title: 'CPU load average of last minute' },
      // No registry entry — falls back to the raw label.
      { name: 'load5', title: 'load5' }
    ])
    await b.metrics('web01', 'CPU load')
    expect(vi.mocked(services.apis.objects.fetchPerfMetrics)).toHaveBeenCalledTimes(1)
    await b.metrics('web01')
    expect(vi.mocked(services.apis.objects.fetchPerfMetrics)).toHaveBeenCalledTimes(2)
  })

  it('returns [] on failure and retries on the next call instead of pinning the error', async () => {
    const aggregation = { id: 'aggr1', title: 'Web shop', pack_id: 'default', function: 'worst' }
    vi.mocked(services.apis.objects.fetchAggregations).mockRejectedValueOnce(new Error('boom'))
    vi.mocked(services.apis.objects.fetchAggregations).mockResolvedValueOnce([aggregation])
    const b = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await b.aggregations()).toEqual([])
    expect(await b.aggregations()).toEqual([aggregation])
  })

  it('short-circuits without a connection or host', async () => {
    const b = runWithServices(services, () => useDataBinding(() => ''))
    expect(await b.aggregations()).toEqual([])
    const c = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await c.metrics('')).toEqual([])
    expect(vi.mocked(services.apis.objects.fetchAggregations)).not.toHaveBeenCalled()
    expect(vi.mocked(services.apis.objects.fetchPerfMetrics)).not.toHaveBeenCalled()
  })
})
