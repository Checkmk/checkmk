<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The card a graph object draws its live metrics in: a heading with the current
reading, a legend where there is more than one curve, and Checkmk's own graph
below.

A single-metric card leads with the value, because that is what an operator
reads off a map at a glance; the curve is context. With several metrics no one
number speaks for the card, so the heading says what the graph is instead.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MetricChart, { type SeriesContext, seriesColorMap } from '@/maps/map/components/MetricChart'
import { useMapPalette } from '@/maps/map/composables/useMapPalette'
import type { MapElementChartModel } from '@/maps/map/elements/composables/useMapElementChart'
import type { ObjectState } from '@/maps/types/api'
import { renderMetricValue } from '@/maps/utils/metricFormat'
import { getMetric, parsePerfData, utilColor, utilPercent } from '@/maps/utils/perf'

import MapElementChartLegend, { type LegendEntry } from './MapElementChartLegend.vue'

const { _t } = usei18n()

const props = defineProps<{
  chart: MapElementChartModel
  state: ObjectState | undefined
  /** The metric the object pinned, if any — it drives the leading reading. */
  pinnedMetric: string | undefined
}>()

const palette = useMapPalette()

const seriesContext = computed<SeriesContext>(() => ({
  unitMap: props.chart.units.value,
  colorMap: props.chart.colors.value,
  titles: props.chart.titles.value,
  palette: palette.value.series
}))

const colors = computed(() => seriesColorMap(props.chart.keys.value, seriesContext.value))

function readingOf(key: string): string {
  const point = props.chart.latest(key)
  return point ? renderMetricValue(point.value, props.chart.units.value[key], point.unit) : ''
}

/** The one series a card leads with, where it draws exactly one. */
const onlySeries = computed(() =>
  props.chart.keys.value.length === 1 ? (props.chart.keys.value[0] ?? null) : null
)

const legend = computed<LegendEntry[]>(() =>
  props.chart.keys.value.map((key, index) => ({
    key,
    label: props.chart.labels.value[index] ?? key,
    color: colors.value[key] ?? 'currentColor',
    value: readingOf(key)
  }))
)

const heading = computed(() => {
  const key = onlySeries.value
  return key === null ? props.chart.headerName.value : (props.chart.titles.value[key] ?? key)
})

/**
 * The leading reading is coloured by how utilised the metric is, so a card
 * turns amber and then red as the value climbs — the colour is the warning, and
 * the operator does not have to read the number to see it.
 */
const readingColor = computed(() => {
  const key = onlySeries.value
  if (key === null) {
    return undefined
  }
  const metric = getMetric(parsePerfData(props.state?.perf_data ?? ''), props.pinnedMetric ?? key)
  return metric ? utilColor(utilPercent(metric)) : colors.value[key]
})
</script>

<template>
  <div class="maps-map-element-chart">
    <div class="maps-map-element-chart__head">
      <span class="maps-map-element-chart__title">{{ heading }}</span>
      <span
        v-if="onlySeries !== null"
        class="maps-map-element-chart__reading"
        :style="{ color: readingColor }"
        >{{ readingOf(onlySeries) }}</span
      >
      <span v-else class="maps-map-element-chart__live">{{ _t('live') }}</span>
    </div>

    <MapElementChartLegend v-if="onlySeries === null" :entries="legend" />

    <div class="maps-map-element-chart__body">
      <MetricChart
        v-for="group in chart.groups.value"
        :key="group.id"
        class="maps-map-element-chart__graph"
        :data="group.data"
        :metric-keys="Object.keys(group.data)"
        :mirrored-keys="group.mirrored"
        :unit-map="chart.units.value"
        :color-map="chart.colors.value"
        :titles="chart.titles.value"
        :window-secs="chart.windowSecs.value"
        :thresholds="chart.thresholds.value"
        :unit="Object.values(group.data)[0]?.at(-1)?.unit"
      />
    </div>
  </div>
</template>

<style scoped>
/* The frame is the object's configured graph_width/height, and this fills it:
   with the page's content-box default the padding and border would paint
   outside the frame, past the selection outline and the resize grip. */
.maps-map-element-chart {
  display: flex;
  overflow: hidden;
  box-sizing: border-box;
  flex-direction: column;
  width: 100%;
  height: 100%;
  padding: 6px 8px 5px;
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  border-radius: 8px;
}

.maps-map-element-chart__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  margin-bottom: var(--dimension-3);
}

.maps-map-element-chart__title {
  overflow: hidden;
  font-size: 9px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.025em;
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-map-element-chart__reading {
  flex-shrink: 0;
  margin-left: var(--dimension-3);
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
}

.maps-map-element-chart__live {
  flex-shrink: 0;
  margin-left: var(--dimension-3);
  font-size: 9px;
  letter-spacing: 0.025em;
  color: var(--font-color-dimmed);
  text-transform: uppercase;
}

.maps-map-element-chart__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  width: 100%;
  min-height: 0;
}

.maps-map-element-chart__graph {
  flex: 1;
  width: 100%;
  min-height: 0;
}
</style>
