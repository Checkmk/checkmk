/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import { perfometerCaption } from '@/maps/map/composables/usePerfometer'
import type { MetricUnitMap, ObjectDetails, ObjectState, PerfometerResult } from '@/maps/types/api'
import { renderMetricValue } from '@/maps/utils/metricFormat'
import { fmtValueWithUnit } from '@/maps/utils/metricScale'
import { type PerfMetric, parsePerfData, utilColor, utilPercent } from '@/maps/utils/perf'

export interface PerfRow {
  label: string
  pct: number
  color: string
  warnPct: number | null
  critPct: number | null
  warnLabel: string
  critLabel: string
  valueLabel: string
}

export interface MainHeadline {
  label: string
  valueLabel: string
  pct: number
  color: string
}

export interface LongOutputRow {
  label: string
  value: string
}

interface PerformanceMetricsOptions {
  state: () => ObjectState | undefined
  details: Ref<ObjectDetails | null>
  perfometer: Ref<PerfometerResult | null>
  // Registered display units per raw perfdata label — value labels then match
  // the Checkmk GUI exactly; omitted metrics fall back to the SI heuristic.
  metricUnits?: Ref<MetricUnitMap>
  // Registry display titles per raw perfdata label; omitted labels render raw.
  metricTitles?: Ref<Record<string, string>>
}

/**
 * Derives the Performance tab's view model from a service's perf_data, the
 * on-demand details (metric titles + long output) and the CMK perfometer:
 * the per-metric utilisation rows, the "main" headline metric, and the
 * structured long-output rows. Pure derivation — no fetching.
 */
export function usePerformanceMetrics(options: PerformanceMetricsOptions) {
  const { state, details, perfometer, metricUnits, metricTitles } = options

  function fmtNum(n: number, unit: string, label?: string): string {
    const spec = label ? metricUnits?.value[label] : undefined
    if (spec) {
      return renderMetricValue(n, spec, unit)
    }
    return fmtValueWithUnit(n, unit)
  }

  const longOutputText = computed(() => details.value?.long_output ?? '')

  const parsedMetrics = computed<PerfMetric[]>(() => {
    const raw = state()?.perf_data
    return raw ? parsePerfData(raw) : []
  })

  function _displayLabel(metricId: string): string {
    return metricTitles?.value[metricId] || metricId
  }

  function _toPerfRow(m: PerfMetric): PerfRow {
    const pct = utilPercent(m)
    const refMax = m.max ?? m.crit ?? null
    const warnPct =
      m.warn !== null && refMax !== null && refMax > 0
        ? Math.min(100, (m.warn / refMax) * 100)
        : null
    const critPct =
      m.crit !== null && refMax !== null && refMax > 0
        ? Math.min(100, (m.crit / refMax) * 100)
        : null
    return {
      label: _displayLabel(m.label),
      pct,
      color: utilColor(pct),
      warnPct,
      critPct,
      warnLabel: m.warn !== null ? fmtNum(m.warn, m.unit, m.label) : '',
      critLabel: m.crit !== null ? fmtNum(m.crit, m.unit, m.label) : '',
      valueLabel: fmtNum(m.value, m.unit, m.label)
    }
  }

  const perfRows = computed<PerfRow[]>(() => parsedMetrics.value.map(_toPerfRow))

  // Pick the metric that best summarizes the service: prefer one with thresholds
  // set (those drive the actual state), then fall back to the highest utilization.
  // Anchors the Performance tab so the operator sees the headline value first.
  const mainMetric = computed<PerfMetric | null>(() => {
    const metrics = parsedMetrics.value
    if (!metrics.length) {
      return null
    }
    const withThresholds = metrics.filter((m) => m.warn !== null || m.crit !== null)
    const candidates = withThresholds.length ? withThresholds : metrics
    return [...candidates].sort((a, b) => utilPercent(b) - utilPercent(a))[0] ?? null
  })

  const mainPerfRow = computed<PerfRow | null>(() =>
    mainMetric.value ? _toPerfRow(mainMetric.value) : null
  )

  const otherPerfRows = computed<PerfRow[]>(() => {
    const main = mainMetric.value?.label
    return perfRows.value.filter((r) => r.label !== main)
  })

  // Long output is a multi-line agent summary; each line tends to be
  // "Label: <value>" — render as a structured two-column list instead of <pre>
  // so it scans like a real summary table.
  const longOutputRows = computed<LongOutputRow[]>(() => {
    const raw = longOutputText.value
    if (!raw) {
      return []
    }
    return raw
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const idx = line.indexOf(':')
        if (idx <= 0) {
          return { label: '', value: line }
        }
        return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() }
      })
  })

  // Headline label/value above the bar — match what Checkmk's own Perf-O-Meter
  // would show (e.g. "RAM usage" for Linux Memory). Falls back to the highest
  // long-output percent line, then to the raw perf_data metric.
  const mainHeadline = computed<MainHeadline | null>(() => {
    const pf = perfometer.value
    const firstPct = pf?.sides[0]?.pct
    if (pf && firstPct !== null && firstPct !== undefined) {
      const pct = Math.min(100, firstPct)
      // The caption already encodes both name and value ("RAM usage 53.88%"),
      // so we don't repeat it as a separate detail line under the bar.
      return { label: perfometerCaption(pf), valueLabel: '', pct, color: utilColor(pct) }
    }
    const longRow = [...longOutputRows.value]
      .map((r) => {
        const pctStr = r.value.match(/(\d+(?:\.\d+)?)\s*%/)?.[1]
        return pctStr && r.label ? { ...r, pct: parseFloat(pctStr) } : null
      })
      .filter((r): r is NonNullable<typeof r> => r !== null)
      .sort((a, b) => b.pct - a.pct)[0]
    if (longRow) {
      const pct = Math.min(100, longRow.pct)
      return { label: longRow.label, valueLabel: longRow.value, pct, color: utilColor(pct) }
    }
    const row = mainPerfRow.value
    if (!row) {
      return null
    }
    return { label: row.label, valueLabel: row.valueLabel, pct: row.pct, color: row.color }
  })

  return {
    perfRows,
    mainMetric,
    mainPerfRow,
    otherPerfRows,
    mainHeadline,
    longOutputRows,
    longOutputText
  }
}
