<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { loadMenu } from '../api/burgerMenu'
import { useGraphInteraction } from '../composables/useGraphInteraction'
import { useGraphVisibility } from '../composables/useGraphVisibility'
import type {
  BurgerMenuCallable,
  BurgerMenuGroup,
  GraphPanelEmits,
  GraphPanelProps,
  RequestedTimeRange,
  TimeRangeCommitKind
} from '../types.ts'
import GraphBrush from './GraphBrush/GraphBrush.vue'
import GraphHeader from './GraphHeader.vue'
import TimeSeriesGraph from './TimeSeriesGraph'
import { deriveYAxis } from './TimeSeriesGraph/yAxis'
import type { ConsolidationFn } from './consolidation'
import {
  CANVAS_MARGIN_HORIZONTAL,
  CANVAS_MARGIN_LEFT,
  MIN_ZOOM_TIME_RANGE_SECONDS
} from './constants'
import GraphLegend from './legend/GraphLegend.vue'

const { _t } = usei18n()

const props = withDefaults(defineProps<GraphPanelProps>(), {
  interactive: true,
  figureWidth: 800,
  figureHeight: 300,
  legendPosition: 'bottom'
})

const emit = defineEmits<GraphPanelEmits>()

const {
  viewTimeRange,
  viewValueRange,
  inspectionActive,
  zoomMode,
  pinTime,
  onZoom,
  onPan,
  onReset,
  onPinCreate,
  clearPin
} = useGraphInteraction(
  () => props.dataTimeRange, // getBaseline
  () => true, // getShowPin; TODO: make this a prop to allow disabling pinning
  () => props.requestedTimeRange, // getRequestedTimeRange
  (timeRange, kind) =>
    updateTimeRange(
      {
        start: timeRange.start,
        end: timeRange.end
      },
      kind
    ) // onTimeRangeCommit
)

const hiddenMetricNames = defineModel<string[]>('hiddenMetricNames', { default: () => [] })
const hiddenLineNames = defineModel<string[]>('hiddenLineNames', { default: () => [] })
const highlightedMetricName = defineModel<string | null>('highlightedMetricName', {
  default: null
})
const {
  visibleMetrics,
  visibleHorizontalLines,
  activeConsolidationFunction,
  setConsolidationFunction
} = useGraphVisibility(
  () => props.metrics,
  () => props.horizontalLines ?? [],
  { hiddenMetricNames, hiddenLineNames, highlightedMetricName }
)

function updateTimeRange(val: RequestedTimeRange, kind: TimeRangeCommitKind) {
  emit('update:requestedTimeRange', val, kind)
}

function updateConsolidationFunction(val: ConsolidationFn) {
  setConsolidationFunction(val)
  emit('update:consolidationFn', val)
}

const yAxis = computed(() => deriveYAxis(props.metrics))

const showBurgerMenu = computed(() => !!props.addType)
const burgerMenuGroups = ref<BurgerMenuGroup[]>([])

if (showBurgerMenu.value) {
  loadMenu(props.addType!)
    .then((groups) => {
      burgerMenuGroups.value = groups
    })
    .catch((err) => {
      throw new Error(`Failed to load menu for addType "${props.addType}": ${err.message}`)
    })
}

const triggerBurgerMenuAction = async (onClick: BurgerMenuCallable) => {
  await onClick(props.internal!)
}
</script>

<template>
  <div class="graphing-graph-panel" :style="{ width: `${figureWidth}px` }">
    <div
      class="graphing-graph-panel__container"
      :class="{ 'graphing-graph-panel__container--legend-right': legendPosition === 'right' }"
    >
      <div class="graphing-graph-panel__canvas-area">
        <!-- TODO: wire the remaining header interactions (consolidation dropdown) into the panel state -->
        <GraphHeader
          v-if="showTitle || showTimestamp || showBurgerMenu || interactive"
          v-model:zoom-mode="zoomMode"
          class="graphing-graph-panel__header"
          :title="title"
          :show-title="showTitle"
          :time-range="dataTimeRange"
          :show-timestamp="showTimestamp"
          :show-controls="interactive"
          :show-consolidation="showConsolidation"
          :show-burger-menu="showBurgerMenu"
          :burger-menu-groups="burgerMenuGroups"
          @do-action="triggerBurgerMenuAction"
        />

        <div
          v-if="dataTimeRange && visibleMetrics.length === 0"
          class="graphing-graph-panel__empty-state"
          :style="{ height: `${figureHeight}px` }"
        >
          {{ _t('All metrics are hidden') }}
        </div>

        <TimeSeriesGraph
          v-else-if="dataTimeRange"
          :time_range="viewTimeRange"
          :metrics="visibleMetrics"
          :horizontal_lines="visibleHorizontalLines"
          :value-range="viewValueRange"
          :zoom-mode="zoomMode"
          :size="{ width: figureWidth, height: figureHeight, mode: 'fixed' }"
          :min-time-range="MIN_ZOOM_TIME_RANGE_SECONDS"
          :min-value-range="null"
          :inspecting="inspectionActive"
          :pan-enabled="interactive"
          :options="{
            header: { title: title ?? null, show_graph_time: false },
            name: title ?? '',
            x_axis: null,
            y_axis: yAxis,
            show_pin: false,
            font_size_pt: 10
          }"
          :highlighted-metric-name="highlightedMetricName"
          :pin-time="pinTime"
          @zoom="onZoom"
          @pan="onPan"
          @reset="onReset"
          @pin-create="onPinCreate"
          @pin-action="clearPin"
        />

        <!--
          The brush spans the full figure width; its plot track mirrors the renderer's
          horizontal margins (plot-left=CANVAS_MARGIN_LEFT, plot-width=figure minus
          CANVAS_MARGIN_HORIZONTAL) so it aligns under the plot.
        -->
        <GraphBrush
          v-if="showBrush && overview && dataTimeRange"
          class="graphing-graph-panel__brush"
          :metrics="overview.metrics"
          :domain="overview.timeRange"
          :window="viewTimeRange"
          :min-span="null"
          :width="figureWidth"
          :plot-left="CANVAS_MARGIN_LEFT"
          :plot-width="figureWidth - CANVAS_MARGIN_HORIZONTAL"
          @update:requested-time-range="updateTimeRange"
        />
      </div>

      <GraphLegend
        v-if="showLegend"
        class="graphing-graph-panel__legend"
        :metrics="metrics"
        :horizontal-lines="horizontalLines ?? []"
        :consolidation-fn="activeConsolidationFunction"
        :hidden-metric-names="hiddenMetricNames"
        :hidden-line-names="hiddenLineNames"
        @update:consolidation-fn="updateConsolidationFunction($event)"
        @update:hidden-metric-names="hiddenMetricNames = $event"
        @update:hidden-line-names="hiddenLineNames = $event"
        @hover-metric="highlightedMetricName = $event"
        @request-show-all="
          () => {
            /* TODO: open metric slideout */
          }
        "
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-panel__header {
  margin-bottom: var(--spacing-double);
}

.graphing-graph-panel__container--legend-right {
  display: flex;
  align-items: flex-start;
  gap: calc(var(--spacing) * 3);
}

.graphing-graph-panel__canvas-area {
  flex: 1;
  min-width: 0;
}

// Visible gap separating the graph from the navigator brush, matching the legend's spacing.
// (CmkTimeSeriesGraph now shrink-wraps its full figure, so the graph's x-axis no longer
// overflows into this space — this margin is a clean gap, not overflow compensation.)
.graphing-graph-panel__brush {
  display: block;
  margin-top: calc(var(--spacing) * 2);
}

.graphing-graph-panel__empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--font-color);
  opacity: 0.5;
  font-size: var(--font-size-small);
}

.graphing-graph-panel__legend {
  margin-top: calc(var(--spacing) * 2);

  .graphing-graph-panel__container--legend-right & {
    width: 480px;
    flex-shrink: 0;
    margin-top: 0;
  }
}
</style>
