<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import useTimer from 'cmk-ui-library/lib/useTimer.ts'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { fetchGraphDataByDefinition, useGraphData } from '../../composables/useGraphData'
import { useGraphInteraction } from '../../composables/useGraphInteraction'
import { useGraphNotice } from '../../composables/useGraphNotice'
import { useGraphVisibility } from '../../composables/useGraphVisibility'
import type { RequestedTimeRange } from '../../types.ts'
import { drawnTimeRange } from '../../utils/timeRange'
import GraphBurgerMenu from '../GraphBurgerMenu.vue'
import GraphNotice from '../GraphNotice.vue'
import GraphTimestamp from '../GraphTimestamp.vue'
import TimeSeriesGraph, { type GraphOptions, type Size, type TimeRange } from '../TimeSeriesGraph'
import { deriveYAxis } from '../TimeSeriesGraph/yAxis'
import { DEFAULT_CONSOLIDATION_FN } from '../consolidation'
import { CANVAS_MARGIN_HORIZONTAL } from '../constants'
import GraphLegendCompact from '../legend/GraphLegendCompact.vue'
import { computeEpochTimeRange } from './computeEpochTimeRange'
import type { GraphFigureProps } from './types.ts'

const { _t } = usei18n()

const MIN_FIGURE_SIZE = 50
const REFRESH_INTERVAL_MS = 60_000
const FONT_SIZE_PT = 8

const props = withDefaults(defineProps<GraphFigureProps>(), {
  combinationMode: null,
  showLegend: false,
  showTimestamp: false,
  showBurgerMenu: false,
  showPin: false,
  burgerMenuGroups: () => [],
  showTimeAxis: true,
  showValueAxis: true,
  showMargin: false
})

const graphAreaDiv = ref<HTMLDivElement | null>(null)
// The renderer draws into this outer figure size and insets the axis/label margins itself, so the
// figure fills the whole measured graph area; subtracting the margins here would double-count them.
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

// The fetch resolution follows the plotted pixel width (figure minus the horizontal axis margins),
// so the requested step matches the columns actually drawn.
const plotWidth = computed(() =>
  Math.max(1, Math.round(figureSize.value.width - CANVAS_MARGIN_HORIZONTAL))
)

// The committed fetch window: the configured range resolved to epochs, or the fixed
// window a time-zoom or pan requested.
const requestedTimeRange = ref<RequestedTimeRange>(computeEpochTimeRange(props.timerange))
const zoomSessionActive = ref(false)

const graphDefinitions = computed(() => [{ internal: props.internal }])

const { graphs, isLoading, error, partialErrors, warnings, reload } = useGraphData(
  () => graphDefinitions.value,
  () => requestedTimeRange.value,
  () => plotWidth.value,
  () => [DEFAULT_CONSOLIDATION_FN],
  () => props.combinationMode,
  { fetchGraph: props.fetchGraph ?? fetchGraphDataByDefinition }
)
const graph = computed(() => graphs.value[0] ?? null)

// Held back so a quick load renders the figure directly, with no icon flashing over it first. A
// failure states itself through the notice below instead.
const showLoadingIcon = useDelayedFlag(
  () => isLoading.value && graph.value === null && error.value === null,
  LOADING_AFFORDANCE_DELAY_MS
)

const notice = useGraphNotice({
  error: () => error.value,
  isLoading: () => isLoading.value,
  partialErrors: () => partialErrors.value,
  warnings: () => warnings.value
})

const refresh = () => {
  requestedTimeRange.value = computeEpochTimeRange(props.timerange)
}
const timer = useTimer(refresh, REFRESH_INTERVAL_MS)

// `start` alone would leave the backoff `reportFailure` scheduled, so stop first: the retry then
// resumes the normal cadence rather than the penalised one.
function onRetry(): void {
  reload()
  timer.stop()
  timer.start()
}

watch(isLoading, (loading) => {
  if (loading || zoomSessionActive.value) {
    return
  }
  if (error.value === null) {
    timer.reportSuccess()
  } else {
    timer.reportFailure()
  }
})

// Both committed time-zoom and pan windows land here: fetch the window and suspend the
// refresh timer so a tick cannot yank the inspected window away; reset resumes it.
const onCommittedTimeRange = (range: RequestedTimeRange) => {
  zoomSessionActive.value = true
  requestedTimeRange.value = { start: range.start, end: range.end }
  timer.stop()
}

const baselineTimeRange = computed<TimeRange | undefined>(() => {
  const served = graph.value?.timeRange
  return served && drawnTimeRange(requestedTimeRange.value, served)
})

const {
  viewTimeRange,
  viewValueRange,
  inspectionActive,
  pinTime,
  onZoom,
  onPan,
  onReset,
  onPinCreate,
  clearPin,
  abandonInspection
} = useGraphInteraction(
  () => baselineTimeRange.value,
  () => props.showPin,
  () => requestedTimeRange.value,
  onCommittedTimeRange
)

watch(
  () => [props.internal, props.combinationMode, JSON.stringify(props.timerange)],
  () => {
    zoomSessionActive.value = false
    abandonInspection()
    refresh()
    timer.start()
  }
)

const {
  hiddenMetricNames,
  hiddenLineNames,
  highlightedMetricName,
  visibleMetrics,
  visibleHorizontalLines
} = useGraphVisibility(
  () => graph.value?.metrics ?? [],
  () => graph.value?.horizontalLines ?? []
)

const onResetIntent = () => {
  onReset()
  if (!zoomSessionActive.value) {
    return
  }
  zoomSessionActive.value = false
  refresh()
  timer.start()
}

// The host's surroundings render the title (e.g. the dashboard widget frame); the graph
// time is shown by the header's GraphTimestamp, not by the renderer.
const graphOptions = computed((): GraphOptions => {
  const effectiveYAxis = deriveYAxis(graph.value?.metrics ?? [], props.yAxis ?? null)

  return {
    name: '',
    header: { title: null, show_graph_time: false },
    x_axis: null,
    y_axis: effectiveYAxis,
    font_size_pt: FONT_SIZE_PT
  }
})

// The marker stands above the plot, in the gap below the header, which is widened to fit it.
// With no header there is no gap and the frame clips it, so the figure reserves the room.
const hasHeader = computed(() => props.showTimestamp || props.showBurgerMenu)

onMounted(() => {
  timer.start()
})

onBeforeUnmount(() => {
  timer.stop()
})
</script>

<template>
  <div
    class="graphing-graph-figure"
    :class="{
      'graphing-graph-figure--with-margin': showMargin,
      'graphing-graph-figure--pin-overhang': showPin && !hasHeader
    }"
  >
    <!-- Initial load only: while a refetch is pending the held data stays rendered
         (the transient zoom bridges it). -->
    <CmkIcon
      v-if="showLoadingIcon"
      name="load-graph"
      size="xlarge"
      class="graphing-graph-figure__loading-icon"
    />
    <template v-else-if="graph">
      <div
        v-if="hasHeader"
        class="graphing-graph-figure__header"
        :class="{ 'graphing-graph-figure__header--pin-gap': showPin }"
      >
        <GraphTimestamp v-if="showTimestamp && baselineTimeRange" :time-range="baselineTimeRange" />
        <GraphBurgerMenu
          v-if="showBurgerMenu"
          :aria-label="_t('Action menu')"
          class="graphing-graph-figure__burger-menu"
          :groups="burgerMenuGroups"
        />
      </div>
      <div
        ref="graphAreaDiv"
        class="graphing-graph-figure__graph"
        :class="{ 'graphing-graph-figure__graph--pinnable': showPin }"
      >
        <TimeSeriesGraph
          :view_time_range="viewTimeRange"
          :data_time_range="graph.timeRange"
          :metrics="visibleMetrics"
          :horizontal_lines="visibleHorizontalLines"
          :value-range="viewValueRange"
          zoom-mode="time"
          :size="figureSize"
          :min-time-range="null"
          :min-value-range="null"
          :inspecting="inspectionActive"
          :pan-enabled="true"
          :zoom-enabled="true"
          :pin-enabled="showPin"
          :pin-time="pinTime"
          :consolidation-function="DEFAULT_CONSOLIDATION_FN"
          :show-time-axis="showTimeAxis"
          :show-value-axis="showValueAxis"
          :min-value-axis-width="minValueAxisWidth"
          :options="graphOptions"
          :highlighted-metric-name="highlightedMetricName"
          @zoom="onZoom"
          @pan="onPan"
          @reset="onResetIntent"
          @pin-create="onPinCreate"
          @pin-action="clearPin"
        />
      </div>
      <GraphLegendCompact
        v-if="showLegend"
        :metrics="graph.metrics"
        :horizontal-lines="graph.horizontalLines"
        :hidden-metric-names="hiddenMetricNames"
        :hidden-line-names="hiddenLineNames"
        @update:hidden-metric-names="hiddenMetricNames = $event"
        @update:hidden-line-names="hiddenLineNames = $event"
        @hover-metric="highlightedMetricName = $event"
      />
    </template>
    <!-- A sibling of the graph rather than a branch beside it, so a failed refetch states itself
         over the data it was going to replace. -->
    <GraphNotice
      v-if="notice"
      v-bind="notice"
      class="graphing-graph-figure__notice"
      @retry="onRetry"
    />
  </div>
</template>

<style scoped>
.graphing-graph-figure {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  position: relative;

  /* The modifiers below pad this box, which fills its container exactly. */
  box-sizing: border-box;
}

.graphing-graph-figure__loading-icon {
  margin: auto;
}

.graphing-graph-figure__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 100%;
}

.graphing-graph-figure__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  padding-top: var(--dimension-3);
  margin-bottom: var(--dimension-4);
}

.graphing-graph-figure__header--pin-gap {
  margin-bottom: var(--dimension-5);
}

.graphing-graph-figure__burger-menu {
  margin-left: auto;
}

.graphing-graph-figure__graph {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.graphing-graph-figure__graph--pinnable {
  overflow: visible;
}

.graphing-graph-figure--with-margin {
  padding: var(--dimension-3);
}

/* Declared after the margin so the overhang keeps the top edge it needs for the marker. */
.graphing-graph-figure--pin-overhang {
  padding-top: var(--dimension-5);
}
</style>
