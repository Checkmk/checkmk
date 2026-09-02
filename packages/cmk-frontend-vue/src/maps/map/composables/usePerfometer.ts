/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import { type MetricInfoBinding, useMetricInfo } from '@/maps/map/composables/useMetricInfo'
import type { PerfometerResult, PerfometerSegment } from '@/maps/types/api'

/**
 * The GUI-rendered CMK Perf-O-Meter for a bound host/service, kept fresh as
 * the streamed perf_data changes. It carries what raw perf_data often lacks:
 * per-side utilization computed from the plugin's focus_range (so gauges can
 * fill even when the metric has no ``max``) and properly formatted value
 * labels. Resolves to null for unbound elements and services without a
 * perfometer definition.
 */
export function usePerfometer(binding: MetricInfoBinding): Ref<PerfometerResult | null> {
  const { info } = useMetricInfo(binding)
  return computed(() => info.value?.perfometer ?? null)
}

/**
 * The GUI paints a Perf-O-Meter's unfilled remainder with its own theme filler,
 * which glares on the glass cards a map draws on. Maps swaps it for the same
 * track colour its gauges use — a token reference, so it follows the theme
 * wherever CSS resolves it.
 */
export const PERFOMETER_REMAINDER_COLOR = 'var(--maps-map-view-gauge-track)'

/** The stack rows restyled for Maps: the GUI theme's background filler
 * segments are swapped for the Maps remainder colour. */
export function displayRows(perfometer: PerfometerResult): PerfometerSegment[][] {
  return perfometer.rows.map((row) =>
    row.map((seg) =>
      seg.color === perfometer.bg_color ? { ...seg, color: PERFOMETER_REMAINDER_COLOR } : seg
    )
  )
}

/** Fill segments (everything that is not background filler) of one stack row. */
export function fillSegments(perfometer: PerfometerResult, row: number): PerfometerSegment[] {
  return (perfometer.rows[row] ?? []).filter((seg) => seg.color !== perfometer.bg_color)
}

/** One side's display text: metric title + CMK-formatted value
 * ("RAM usage 8.32 GiB"); falls back to the bare value label. */
export function sideCaption(perfometer: PerfometerResult, side: number): string | null {
  const s = perfometer.sides[side]
  if (!s) {
    return null
  }
  return s.title ? `${s.title} ${s.label}` : s.label
}

/** Titled caption across all sides ("In 244 bit/s / Out 131 bit/s");
 * falls back to the plain views label when no side resolved. */
export function perfometerCaption(perfometer: PerfometerResult): string {
  const parts = perfometer.sides
    .map((_, i) => sideCaption(perfometer, i))
    .filter((p): p is string => !!p)
  return parts.length ? parts.join(' / ') : perfometer.label
}
