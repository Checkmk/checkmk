<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A Maps metric series, drawn by Checkmk's own graph.

The component is only the adapter: it measures the box it was given, puts the
irregularly polled samples on the regular grid the graph reads (``resample``),
and translates units, colours and thresholds into the graph's data leg
(``series``). Everything visual — axes, curves, hover, theming — is
``TimeSeriesGraph``'s, so a Maps graph reads exactly like a Checkmk graph.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, ref, useTemplateRef } from 'vue'

import TimeSeriesGraph from '@/graphing/components/TimeSeriesGraph'
import type { ShadedRegion } from '@/graphing/components/TimeSeriesGraph/types'
import { deriveYAxis } from '@/graphing/components/TimeSeriesGraph/yAxis'
import { useMapPalette } from '@/maps/map/composables/useMapPalette'
import type { MetricPoint, MetricUnitMap } from '@/maps/types/api'

import { deriveGrid } from './resample'
import { buildGraphMetrics, buildThresholdLines } from './series'

const { _t } = usei18n()

/**
 * A map draws curves and their threshold lines, nothing else — shaded bands
 * belong to the graph designer. Held as one value so the graph's own computed
 * properties are not invalidated by a fresh array on every render.
 */
const SHADED_REGIONS: ShadedRegion[] = []

const props = defineProps<{
  /** Polled samples per raw perfdata label. */
  data: Record<string, MetricPoint[]>
  /** Which labels to draw, in drawing order. */
  metricKeys: string[]
  /** Labels drawn below the axis (a bidirectional graph's lower half). */
  mirroredKeys?: string[]
  /**
   * Checkmk's registered display semantics per label (unit, translation scale,
   * series colour). Absent labels fall back to a reading of their raw unit.
   */
  unitMap?: MetricUnitMap
  colorMap?: Record<string, string>
  titles?: Record<string, string>
  /** Width of the drawn time window, in seconds. */
  windowSecs: number
  /** Warn/crit levels of the leading metric, drawn as guide lines. */
  thresholds: { warn: number | null; crit: number | null } | null
  /** Perfdata unit for labels with no registry entry. */
  unit: string | undefined
}>()

const root = useTemplateRef<HTMLElement>('root')
const size = ref({ width: 0, height: 0 })
useResizeObserver(([entry]) => {
  if (entry) {
    size.value = {
      width: entry.contentRect.width,
      height: entry.contentRect.height
    }
  }
}).observe(root)

const palette = useMapPalette()

const context = computed(() => ({
  unitMap: props.unitMap,
  colorMap: props.colorMap,
  titles: props.titles,
  mirroredKeys: props.mirroredKeys,
  fallbackUnit: props.unit,
  palette: palette.value.series
}))

const grid = computed(() =>
  deriveGrid(
    props.metricKeys.map((key) => props.data[key] ?? []),
    props.windowSecs,
    Date.now() / 1000
  )
)

const metrics = computed(() =>
  buildGraphMetrics(props.data, props.metricKeys, grid.value, context.value)
)

const horizontalLines = computed(() =>
  buildThresholdLines(
    props.thresholds,
    props.data,
    props.metricKeys[0],
    context.value,
    { warn: _t('Warning'), crit: _t('Critical') },
    { warn: palette.value.state('WARNING'), crit: palette.value.state('CRITICAL') }
  )
)

const timeRange = computed(() => ({
  start: grid.value.start,
  end: grid.value.end,
  step: grid.value.step
}))

const yAxis = computed(() => deriveYAxis(metrics.value))

/** Nothing to draw before the box has been laid out. */
const drawable = computed(() => size.value.width > 0 && size.value.height > 0)
</script>

<template>
  <div ref="root" class="maps-metric-chart">
    <TimeSeriesGraph
      v-if="drawable"
      :view_time_range="timeRange"
      :metrics="metrics"
      :horizontal_lines="horizontalLines"
      :shaded_regions="SHADED_REGIONS"
      :size="{ width: size.width, height: size.height, mode: 'fixed' }"
      :value-range="null"
      :zoom-mode="'time'"
      :min-time-range="null"
      :min-value-range="null"
      :inspecting="false"
      :pan-enabled="false"
      :zoom-enabled="false"
      :highlighted-metric-names="[]"
      :options="{
        header: { title: null, show_graph_time: false },
        name: '',
        x_axis: null,
        y_axis: yAxis,
        font_size_pt: 7
      }"
    />
  </div>
</template>

<style scoped>
.maps-metric-chart {
  width: 100%;
  height: 100%;
}
</style>
