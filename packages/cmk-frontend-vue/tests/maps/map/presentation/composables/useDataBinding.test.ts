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

  it('caches host lookups per connection', async () => {
    vi.mocked(services.apis.objects.fetchObjects).mockResolvedValue(['web01', 'web02'])
    const b = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await b.hosts()).toEqual(['web01', 'web02'])
    expect(await b.hosts()).toEqual(['web01', 'web02'])
    expect(vi.mocked(services.apis.objects.fetchObjects)).toHaveBeenCalledTimes(1)

    const other = runWithServices(services, () => useDataBinding(() => 'live_2'))
    await other.hosts()
    expect(vi.mocked(services.apis.objects.fetchObjects)).toHaveBeenCalledTimes(2)
  })

  it('caches services per host and metrics per host/service', async () => {
    vi.mocked(services.apis.objects.fetchObjects).mockResolvedValue(['CPU load'])
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
    await b.services('web01')
    await b.services('web01')
    expect(vi.mocked(services.apis.objects.fetchObjects)).toHaveBeenCalledTimes(1)
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
    vi.mocked(services.apis.objects.fetchObjects).mockRejectedValueOnce(new Error('boom'))
    vi.mocked(services.apis.objects.fetchObjects).mockResolvedValueOnce(['web01'])
    const b = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await b.hosts()).toEqual([])
    expect(await b.hosts()).toEqual(['web01'])
  })

  it('serves groups and BI aggregations from their own cached sources', async () => {
    vi.mocked(services.apis.objects.fetchObjects).mockResolvedValue(['linux'])
    vi.mocked(services.apis.objects.fetchAggregations).mockResolvedValue([
      { id: 'aggr1', title: 'Web shop', pack_id: 'default', function: 'worst' }
    ])
    const b = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await b.hostgroups()).toEqual(['linux'])
    expect(vi.mocked(services.apis.objects.fetchObjects)).toHaveBeenCalledWith('hostgroup')
    await b.servicegroups()
    expect(vi.mocked(services.apis.objects.fetchObjects)).toHaveBeenCalledWith('servicegroup')
    const aggs = await b.aggregations()
    expect(aggs[0]!.title).toBe('Web shop')
    await b.aggregations()
    expect(vi.mocked(services.apis.objects.fetchAggregations)).toHaveBeenCalledTimes(1)
  })

  it('short-circuits without a connection or host', async () => {
    const b = runWithServices(services, () => useDataBinding(() => ''))
    expect(await b.hosts()).toEqual([])
    const c = runWithServices(services, () => useDataBinding(() => 'live_1'))
    expect(await c.services('')).toEqual([])
    expect(vi.mocked(services.apis.objects.fetchObjects)).not.toHaveBeenCalled()
  })
})
