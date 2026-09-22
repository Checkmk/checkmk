/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMetricCatalog } from '@/maps/map/composables/useMetricInfo'
import { useMapsApis } from '@/maps/services/context'
import type { AggregationInfo, MetricChoice } from '@/maps/types/api'

// Shared host/service/group/metric lookups for every binding surface
// (inspector, data panel, connect-data popover). Results are cached per
// connection so opening the inspector on ten elements fetches the host list
// once; a failed fetch is evicted so the next call retries instead of pinning
// an empty list.
const cache = new Map<string, Promise<unknown>>()

function cached<T>(key: string, fetcher: () => Promise<T>, empty: T): Promise<T> {
  const hit = cache.get(key)
  if (hit) {
    return hit as Promise<T>
  }
  const p = fetcher().catch(() => {
    cache.delete(key)
    return empty
  })
  cache.set(key, p)
  return p
}

export function clearDataBindingCache(): void {
  cache.clear()
}

export function useDataBinding(connectionId: () => string) {
  const { objects } = useMapsApis()
  const { fetchMetricChoices } = useMetricCatalog()

  function objectNames(type: 'host' | 'hostgroup' | 'servicegroup'): Promise<string[]> {
    const conn = connectionId()
    if (!conn) {
      return Promise.resolve([])
    }
    return cached(`${type}|${conn}`, () => objects.fetchObjects(type), [])
  }

  function hosts(): Promise<string[]> {
    return objectNames('host')
  }

  function hostgroups(): Promise<string[]> {
    return objectNames('hostgroup')
  }

  function servicegroups(): Promise<string[]> {
    return objectNames('servicegroup')
  }

  function aggregations(): Promise<AggregationInfo[]> {
    const conn = connectionId()
    if (!conn) {
      return Promise.resolve([])
    }
    return cached(`aggregations|${conn}`, () => objects.fetchAggregations(), [])
  }

  function services(host: string): Promise<string[]> {
    const conn = connectionId()
    if (!conn || !host) {
      return Promise.resolve([])
    }
    return cached(`services|${conn}|${host}`, () => objects.fetchObjects('service', host), [])
  }

  function metrics(host: string, service?: string | null): Promise<MetricChoice[]> {
    const conn = connectionId()
    if (!conn || !host) {
      return Promise.resolve([])
    }
    return cached(
      `metrics|${conn}|${host}|${service ?? ''}`,
      () => fetchMetricChoices(host, service ?? null),
      []
    )
  }

  return { hosts, hostgroups, servicegroups, aggregations, services, metrics }
}
