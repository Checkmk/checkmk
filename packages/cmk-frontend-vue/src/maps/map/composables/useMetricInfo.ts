/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { MetricInfoGraphContext } from '@/maps/api/metricInfo'
import { useMapsApis } from '@/maps/services/context'
import type { MetricChoice, MetricGraphGroup, MetricInfoResult } from '@/maps/types/api'

export interface MetricInfoBinding {
  // Cache identity only — the fetch itself is a pure function of
  // (perf_data, check_command); keying the cache by the bound object keeps it
  // bounded by map size instead of growing with every state tick.
  connectionId: () => string | null | undefined
  hostName: () => string | null | undefined
  serviceDescription: () => string | null | undefined
  perfData: () => string | null | undefined
  checkCommand: () => string | null | undefined
  // Also resolve the applicable graph groups (graph widgets need them; the
  // evaluation is a walk over every registered graph plugin, so it stays
  // opt-in). siteId completes the object identity for the evaluation.
  graphs?: () => boolean
  siteId?: () => string | null | undefined
  enabled: () => boolean
}

/**
 * The CMK display semantics for a bound host/service, kept fresh as the
 * streamed perf_data changes: the GUI-rendered Perf-O-Meter plus, per raw
 * perfdata label, the registry title, display unit and scale (and, opt-in,
 * the applicable graph groups). Resolves to null for unbound elements and
 * while nothing has been fetched yet; consumers fall back to client-side
 * heuristics.
 */
export function useMetricInfo(binding: MetricInfoBinding): {
  info: Ref<MetricInfoResult | null>
  pending: Ref<boolean>
} {
  const { metricInfo } = useMapsApis()
  const info = ref<MetricInfoResult | null>(null)
  const pending = ref(false)
  // Monotonic epoch: a slow response for an older binding/tick must not
  // overwrite the value of a newer one (last-write-wins races).
  let seq = 0

  async function fetchNow(): Promise<void> {
    const host = binding.hostName()
    const service = binding.serviceDescription()
    const perfData = binding.perfData() ?? ''
    if (!binding.enabled() || !host || !service || !perfData.trim()) {
      seq++
      info.value = null
      pending.value = false
      return
    }
    const epoch = ++seq
    const withGraphs = binding.graphs?.() ?? false
    // NUL-joined: hosts and services legitimately contain spaces. The graphs
    // flag is part of the identity — a graph widget and a gadget bound to the
    // same service need different responses.
    const identity = [binding.connectionId() ?? '', host, service, String(withGraphs)].join(
      '\u0000'
    )
    const snapshot = [binding.checkCommand() ?? '', perfData].join('\u0000')
    const graphContext: MetricInfoGraphContext | undefined = withGraphs
      ? { hostName: host, serviceDescription: service, siteId: binding.siteId?.() ?? '' }
      : undefined
    pending.value = true
    // Shared across all subscribers: one request per bound object and
    // (perf_data, check_command) snapshot, so a wall of gadgets bound to the
    // same service fires a single fetch per state tick.
    const value = await metricInfo.resolveShared({
      identity,
      snapshot,
      perfData,
      checkCommand: binding.checkCommand() ?? '',
      graphContext
    })
    if (epoch === seq) {
      info.value = value
      pending.value = false
    }
  }

  watch(
    [
      binding.enabled,
      binding.connectionId,
      binding.hostName,
      binding.serviceDescription,
      binding.perfData,
      binding.checkCommand,
      () => binding.graphs?.() ?? false
    ],
    () => void fetchNow(),
    { immediate: true }
  )

  return { info, pending }
}

/**
 * Lookups over what a host or service actually measures: the raw perfdata labels
 * and the graphs Checkmk would draw for them.
 *
 * The perfdata source and its display semantics come from two different
 * endpoints, and every caller needs both, so they are resolved together here.
 */
export function useMetricCatalog(): {
  fetchMetricChoices: (host: string, service: string | null) => Promise<MetricChoice[]>
  fetchGraphTemplates: (
    host: string,
    service: string | null,
    siteId: string | null
  ) => Promise<MetricGraphGroup[]>
} {
  const { objects, metricInfo } = useMapsApis()

  return {
    async fetchMetricChoices(host: string, service: string | null): Promise<MetricChoice[]> {
      const source = await objects.fetchPerfMetrics(host, service ?? undefined)
      if (!source.metrics.length) {
        return []
      }
      const info = await metricInfo
        .resolve(source.perf_data, source.check_command)
        .catch(() => null)
      return source.metrics.map((name) => ({
        name,
        title: info?.metrics[name]?.title ?? name
      }))
    },

    async fetchGraphTemplates(
      host: string,
      service: string | null,
      siteId: string | null
    ): Promise<MetricGraphGroup[]> {
      const source = await objects.fetchPerfMetrics(host, service ?? undefined)
      if (!source.perf_data.trim()) {
        return []
      }
      const info = await metricInfo.resolve(source.perf_data, source.check_command, {
        hostName: host,
        serviceDescription: service,
        siteId
      })
      return info.graphs ?? []
    }
  }
}
