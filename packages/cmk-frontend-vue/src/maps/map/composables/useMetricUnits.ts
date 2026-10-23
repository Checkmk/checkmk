/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import { type MetricInfoBinding, useMetricInfo } from '@/maps/map/composables/useMetricInfo'
import type { MetricInfoResult, MetricUnitMap } from '@/maps/types/api'

/** Flatten the metric-info entries into the {unit + scale} shape the value
 * formatters (renderMetricValue) consume, keyed by raw perfdata label. */
export function metricUnitsOf(info: MetricInfoResult | null): MetricUnitMap {
  return Object.fromEntries(
    Object.entries(info?.metrics ?? {}).map(([label, entry]) => [
      label,
      { ...entry.unit, scale: entry.scale }
    ])
  )
}

/** Registry series colours per raw perfdata label, so a Maps graph draws a
 * metric in the same colour Checkmk's graphs do. Unregistered labels are
 * absent — callers fall back to their own palette. */
export function metricColorsOf(info: MetricInfoResult | null): Record<string, string> {
  return Object.fromEntries(
    Object.entries(info?.metrics ?? {}).map(([label, entry]) => [label, entry.color])
  )
}

/** Registry display titles per raw perfdata label; unregistered labels are
 * absent — callers fall back to the raw label. */
export function metricTitlesOf(info: MetricInfoResult | null): Record<string, string> {
  return Object.fromEntries(
    Object.entries(info?.metrics ?? {}).map(([label, entry]) => [label, entry.title])
  )
}

/**
 * The CMK metric-registry display units for a bound host/service — keyed by
 * raw perfdata label. Resolves to {} for unbound elements and services whose
 * metrics aren't registered; consumers fall back to client-side heuristics
 * via renderMetricValue.
 */
export function useMetricUnits(binding: MetricInfoBinding): Ref<MetricUnitMap> {
  const { info } = useMetricInfo(binding)
  return computed(() => metricUnitsOf(info.value))
}
