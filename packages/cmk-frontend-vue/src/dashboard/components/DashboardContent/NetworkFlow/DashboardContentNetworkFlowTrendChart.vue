<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, inject, ref, watch } from 'vue'

import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { explicitWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type { NetworkFlowTrendChartContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import {
  GraphLegendCompact,
  type GraphOptions,
  type Metric,
  type RequestedTimeRange,
  type Size,
  type TimeRange,
  TimeSeriesGraph,
  deriveYAxis,
  useGraphInteraction,
  useGraphVisibility
} from '@/graphing'
import { autonomousSystemSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

import WidgetFigureFrame from '../figures/WidgetFigureFrame.vue'
import type { ContentProps } from '../types.ts'
import { trendChartMetrics } from './trendChartMetrics.ts'

const props = defineProps<ContentProps<NetworkFlowTrendChartContent>>()

const MIN_FIGURE_SIZE = 50
const FONT_SIZE_PT = 8

// null when the dashboard does not wire it up; series names then stay plain text.
const openAutonomousSystemSlideIn = inject(autonomousSystemSlideInKey, null)

const graphAreaDiv = ref<HTMLDivElement | null>(null)
// The renderer insets the axis margins itself, so it wants the whole measured area.
const figureSize = ref<Size>({ width: 800, height: 200, mode: 'resizable' })
const { observe } = useResizeObserver((entries) => {
  const size = entries[0]!.contentBoxSize![0]!
  figureSize.value = {
    width: Math.max(MIN_FIGURE_SIZE, size.inlineSize),
    height: Math.max(MIN_FIGURE_SIZE, size.blockSize),
    mode: 'resizable'
  }
})
observe(graphAreaDiv)

// The window a zoom or a pan committed. While it is null the backend resolves
// the window from the time filter, which is also what a reset returns to.
const zoomedRange = ref<RequestedTimeRange | null>(null)

// Declared before the fetch below so it has already dropped a stale zoom by the
// time the changed parameters trigger the refetch.
watch(
  () => JSON.stringify({ filters: props.effective_filter_context.filters, content: props.content }),
  () => {
    zoomedRange.value = null
  }
)

const { state, retry } = useWidgetData(
  () =>
    dashboardAPI.computeNetworkFlowTrendChart({
      source: explicitWidgetSource(props),
      ...(zoomedRange.value === null ? {} : { requested_time_range: zoomedRange.value })
    }),
  () => [props.content, props.effective_filter_context, zoomedRange.value],
  () => props.tick
)

const chart = computed(() => (state.value.kind === 'data' ? state.value.value : null))

// The display mode only restacks the series that are already there, so switching
// it does not wait for a new response.
const metrics = computed((): Metric[] =>
  trendChartMetrics(
    (chart.value?.series ?? []).map((item) => ({ name: item.name, dataPoints: item.data_points })),
    props.content.display_mode
  )
)

const fetchedTimeRange = computed((): TimeRange | undefined => chart.value?.time_range)

const {
  viewTimeRange,
  viewValueRange,
  inspectionActive,
  onZoom,
  onPan,
  onReset,
  abandonInspection
} = useGraphInteraction(
  () => fetchedTimeRange.value,
  () => false,
  () => zoomedRange.value ?? { start: 0, end: 0 },
  (range) => {
    zoomedRange.value = { start: range.start, end: range.end }
  }
)

watch(zoomedRange, (range) => {
  if (range === null) {
    abandonInspection()
  }
})

const onResetIntent = (): void => {
  onReset()
  zoomedRange.value = null
}

const {
  hiddenMetricNames,
  hiddenLineNames,
  highlightedMetricNames,
  visibleMetrics,
  visibleHorizontalLines
} = useGraphVisibility(
  () => metrics.value,
  () => []
)

// The autonomous_systems dimension labels its series "AS<n>"; make those open
// the AS detail slide-in.
const clickableMetricNames = computed(() =>
  props.content.dimension === 'autonomous_systems' && openAutonomousSystemSlideIn !== null
    ? metrics.value.map((metric) => metric.metadata.name)
    : []
)

function onMetricClick(name: string): void {
  if (!openAutonomousSystemSlideIn) {
    return
  }
  const asn = Number(name.replace(/^AS/, ''))
  if (!Number.isNaN(asn)) {
    openAutonomousSystemSlideIn(asn)
  }
}

// The widget frame renders the title, and the time axis needs no separate label.
const graphOptions = computed(
  (): GraphOptions => ({
    name: '',
    header: { title: null, show_graph_time: false },
    x_axis: null,
    y_axis: deriveYAxis(metrics.value),
    font_size_pt: FONT_SIZE_PT
  })
)
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <div class="db-content-network-flow-trend-chart__wrapper">
      <template v-if="chart !== null">
        <div ref="graphAreaDiv" class="db-content-network-flow-trend-chart__graph">
          <TimeSeriesGraph
            :view_time_range="viewTimeRange"
            :data_time_range="fetchedTimeRange"
            :metrics="visibleMetrics"
            :horizontal_lines="visibleHorizontalLines"
            :shaded_regions="[]"
            :value-range="viewValueRange"
            zoom-mode="time"
            :size="figureSize"
            :bin-unit="null"
            :min-time-range="null"
            :min-value-range="null"
            :inspecting="inspectionActive"
            :pan-enabled="true"
            :zoom-enabled="true"
            :options="graphOptions"
            :highlighted-metric-names="highlightedMetricNames"
            @zoom="onZoom"
            @pan="onPan"
            @reset="onResetIntent"
          />
        </div>
        <GraphLegendCompact
          v-if="content.show_legend"
          :metrics="metrics"
          :hidden-metric-names="hiddenMetricNames"
          :hidden-line-names="hiddenLineNames"
          :clickable-metric-names="clickableMetricNames"
          @update:hidden-metric-names="hiddenMetricNames = $event"
          @update:hidden-line-names="hiddenLineNames = $event"
          @hover-metrics="highlightedMetricNames = $event"
          @metric-click="onMetricClick"
        />
      </template>
    </div>
  </WidgetFigureFrame>
</template>

<style scoped>
.db-content-network-flow-trend-chart__wrapper {
  display: flex;
  box-sizing: border-box;
  flex-direction: column;
  height: 100%;
  padding: calc(var(--spacing) * 2);
}

.db-content-network-flow-trend-chart__graph {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}
</style>
