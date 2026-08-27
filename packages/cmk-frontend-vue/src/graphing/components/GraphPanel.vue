<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, ref, watch } from 'vue'

import { loadMenu } from '../api/burgerMenu'
import { useGraphInteraction } from '../composables/useGraphInteraction'
import { useGraphVisibility } from '../composables/useGraphVisibility'
import type {
  BurgerMenuCallable,
  BurgerMenuGroup,
  GraphPanelEmits,
  GraphPanelProps,
  RequestedTimeRange,
  TimeInterval,
  TimeRange,
  TimeRangeCommitKind
} from '../types.ts'
import { drawnTimeRange } from '../utils/timeRange'
import GraphBrush from './GraphBrush/GraphBrush.vue'
import TimeSeriesGraph, { type ZoomPayload } from './TimeSeriesGraph'
import { deriveYAxis } from './TimeSeriesGraph/yAxis'
import { type ConsolidationFn, DEFAULT_CONSOLIDATION_FN } from './consolidation'
import { CANVAS_MARGIN_LEFT, MIN_ZOOM_TIME_RANGE_SECONDS, PLOT_INSET_X } from './constants'
import GraphHeader from './header/GraphHeader.vue'
import GraphLegend from './legend/GraphLegend.vue'

const { _t } = usei18n()

const props = withDefaults(defineProps<GraphPanelProps>(), {
  figureHeight: 300,
  legendPosition: 'bottom'
})

const emit = defineEmits<GraphPanelEmits>()

// The step only reaches `timestampAt` in the renderer's decimation, which walks the metrics. A
// fetch assigns the data range and the metrics together, so this stands in only when there are no
// curves at all and nothing reads it.
const NOMINAL_STEP_SECONDS = 60

const baselineTimeRange = computed<TimeRange>(() => {
  if (!props.dataTimeRange) {
    return { ...props.requestedTimeRange, step: NOMINAL_STEP_SECONDS }
  }
  return props.awaitingData
    ? props.dataTimeRange
    : drawnTimeRange(props.requestedTimeRange, props.dataTimeRange)
})

const headerTimeRange = computed<TimeRange | undefined>(() =>
  props.dataTimeRange ? baselineTimeRange.value : undefined
)

const {
  viewTimeRange,
  viewValueRange,
  transientTimeRange,
  inspectionActive,
  zoomMode,
  pinTime,
  onZoom,
  onPan,
  onBrush,
  onReset,
  abandonInspection,
  onPinCreate,
  clearPin
} = useGraphInteraction(
  () => baselineTimeRange.value, // getBaseline
  () => props.interaction.pin === 'enabled', // getShowPin
  () => props.requestedTimeRange, // getRequestedTimeRange
  updateTimeRange // onTimeRangeCommit
)

watch(() => props.timePickerRequests, abandonInspection)

function onZoomIntent(payload: ZoomPayload): void {
  emit('inspect')
  onZoom(payload)
}

function onPanIntent(payload: { timeRange: TimeRange }): void {
  emit('inspect')
  onPan(payload)
}

function onBrushIntent(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
  emit('inspect')
  onBrush(range, kind)
}

const hiddenMetricNames = defineModel<string[]>('hiddenMetricNames', { default: () => [] })
const hiddenLineNames = defineModel<string[]>('hiddenLineNames', { default: () => [] })
const highlightedMetricName = defineModel<string | null>('highlightedMetricName', {
  default: null
})
const consolidationFn = defineModel<ConsolidationFn>('consolidationFn', {
  default: DEFAULT_CONSOLIDATION_FN
})
const { visibleMetrics, visibleHorizontalLines } = useGraphVisibility(
  () => props.metrics,
  () => props.horizontalLines ?? [],
  { hiddenMetricNames, hiddenLineNames, highlightedMetricName }
)

const { visibleMetrics: visibleBrushMetrics } = useGraphVisibility(
  () => props.brushSnapshot?.data.metrics ?? [],
  () => [],
  { hiddenMetricNames }
)

function updateTimeRange(val: RequestedTimeRange, kind: TimeRangeCommitKind) {
  // The served window is a storage step wider; adopting its span would grow it on every pan.
  const asked = props.requestedTimeRange
  const end = kind === 'translated_timerange' ? val.start + (asked.end - asked.start) : val.end
  emit('update:requestedTimeRange', { start: val.start, end }, kind)
}

// Backend-hidden metrics (stack references, render.hidden) are structural: they feed the
// stacking baseline in the renderer but are never listed, counted, or toggled by the user.
const legendMetrics = computed(() => props.metrics.filter((metric) => !metric.render.hidden))
const anyMetricShown = computed(() => visibleMetrics.value.some((metric) => !metric.render.hidden))

// Time zoom clamps the *requested* window at the floor, so that is the range which reaches it;
// the served window stays a step wider and would never compare equal.
const atMinTimeZoom = computed(
  () => props.requestedTimeRange.end - props.requestedTimeRange.start <= MIN_ZOOM_TIME_RANGE_SECONDS
)

const yAxis = computed(() => deriveYAxis(props.metrics))

// The add-to target is what the burger menu exists for, so it carries everything the actions
// need: the type the menu is assembled for, the specification most of them replay and the built
// graph a custom graph stores.
const addTo = computed(() => props.addTo ?? null)
const showBurgerMenu = computed(
  () => addTo.value !== null && props.interaction.burger === 'enabled'
)
const burgerMenuGroups = ref<BurgerMenuGroup[]>([])

const initialAddTo = addTo.value
if (showBurgerMenu.value && initialAddTo !== null) {
  loadMenu(initialAddTo.type)
    .then((groups) => {
      burgerMenuGroups.value = groups
    })
    .catch((err) => {
      throw new Error(`Failed to load menu for add type "${initialAddTo.type}": ${err.message}`)
    })
}

const triggerBurgerMenuAction = async (onClick: BurgerMenuCallable) => {
  const target = addTo.value
  if (target === null) {
    throw new Error('A burger menu action needs the add-to target the menu was assembled for')
  }
  // The export builds its request around the displayed range, so every action is handed the graph
  // as the backends address it.
  await onClick({
    specification: target.specification,
    internal: target.internal,
    timeStart: props.requestedTimeRange.start,
    timeEnd: props.requestedTimeRange.end,
    consolidationFunction: consolidationFn.value
  })
}

const zoomControlsEnabled: Ref<boolean> = computed(
  () => props.interaction.zoom === 'enabled' || props.interaction.panning === 'enabled'
)

const showGraphHeader: Ref<boolean> = computed(
  () =>
    props.showTitle ||
    props.showTimestamp ||
    props.interaction.burger === 'enabled' ||
    zoomControlsEnabled.value ||
    props.showConsolidation
)

// Not `viewTimeRange`: that is what the curves are drawn against, which during a refetch is
// still the range the previous data covered.
const brushWindow = computed<TimeInterval | undefined>(
  () => transientTimeRange.value ?? props.brushSnapshot?.window
)

// The renderer sizes its own value-axis margin to the labels it draws; the brush track mirrors
// it so the strip stays under the plot.
const plotLeft = ref(CANVAS_MARGIN_LEFT)
const brushPlotWidth = computed(() => props.figureWidth - plotLeft.value - PLOT_INSET_X)
</script>

<template>
  <div class="graphing-graph-panel" :style="{ width: `${figureWidth}px` }">
    <div
      class="graphing-graph-panel__container"
      :class="{ 'graphing-graph-panel__container--legend-right': legendPosition === 'right' }"
    >
      <div class="graphing-graph-panel__canvas-area">
        <GraphHeader
          v-if="showGraphHeader"
          v-model:zoom-mode="zoomMode"
          v-model:consolidation-fn="consolidationFn"
          class="graphing-graph-panel__header"
          :class="{ 'graphing-graph-panel__header--compact': headerIsCompact }"
          :title="title"
          :show-title="showTitle"
          :time-range="headerTimeRange"
          :show-timestamp="showTimestamp"
          :show-controls="zoomControlsEnabled"
          :show-consolidation="showConsolidation"
          :show-burger-menu="showBurgerMenu"
          :burger-menu-groups="burgerMenuGroups"
          :is-compact="headerIsCompact"
          @do-action="triggerBurgerMenuAction"
        />

        <div
          class="graphing-graph-panel__plot"
          :class="{ 'graphing-graph-panel__plot--inert': !anyMetricShown }"
        >
          <TimeSeriesGraph
            :view_time_range="viewTimeRange"
            :data_time_range="dataTimeRange"
            :metrics="visibleMetrics"
            :horizontal_lines="visibleHorizontalLines"
            :value-range="viewValueRange"
            :zoom-mode="zoomMode"
            :size="{ width: figureWidth, height: figureHeight, mode: 'fixed' }"
            :min-time-range="MIN_ZOOM_TIME_RANGE_SECONDS"
            :at-min-time-zoom="atMinTimeZoom"
            :min-value-range="null"
            :consolidation-function="consolidationFn"
            :inspecting="inspectionActive"
            :pan-enabled="interaction.panning === 'enabled'"
            :zoom-enabled="interaction.zoom === 'enabled'"
            :pin-enabled="interaction.pin === 'enabled'"
            :options="{
              header: { title: title ?? null, show_graph_time: false },
              name: title ?? '',
              x_axis: null,
              y_axis: yAxis,
              font_size_pt: 10
            }"
            :highlighted-metric-name="highlightedMetricName"
            :pin-time="pinTime"
            @zoom="onZoomIntent"
            @pan="onPanIntent"
            @reset="onReset"
            @pin-create="onPinCreate"
            @pin-action="clearPin"
            @update:plot-left="plotLeft = $event"
          />
          <CmkAlertBox
            v-if="dataTimeRange && !anyMetricShown"
            class="graphing-graph-panel__empty-state"
            variant="info"
          >
            {{ _t('All metrics are hidden') }}
          </CmkAlertBox>
        </div>

        <GraphBrush
          v-if="interaction.brush === 'enabled' && brushSnapshot && brushWindow && dataTimeRange"
          class="graphing-graph-panel__brush"
          :metrics="visibleBrushMetrics"
          :domain="brushSnapshot.drawnDomain"
          :data-domain="brushSnapshot.data.dataTimeRange"
          :window="brushWindow"
          :consolidation-fn="consolidationFn"
          :min-span="null"
          :width="figureWidth"
          :plot-left="plotLeft"
          :plot-width="brushPlotWidth"
          @update:requested-time-range="onBrushIntent"
        />
      </div>

      <GraphLegend
        v-if="showLegend"
        class="graphing-graph-panel__legend"
        :metrics="legendMetrics"
        :horizontal-lines="horizontalLines ?? []"
        :consolidation-fn="consolidationFn"
        :hidden-metric-names="hiddenMetricNames"
        :hidden-line-names="hiddenLineNames"
        @update:hidden-metric-names="hiddenMetricNames = $event"
        @update:hidden-line-names="hiddenLineNames = $event"
        @hover-metric="highlightedMetricName = $event"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
// Transparent and borderless by default.
// A context (e.g. the graph icon hover; _graphs.scss) defines these css variables and by that
// handles background and border color of the panel.
.graphing-graph-panel {
  background-color: var(--cmk-graph-panel-bg, transparent);
  border: var(--cmk-graph-panel-border, none);
}

.graphing-graph-panel__header {
  margin-bottom: var(--dimension-3);
}

.graphing-graph-panel__header--compact {
  margin: var(--spacing-half) var(--spacing);
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

.graphing-graph-panel__plot {
  position: relative;
}

.graphing-graph-panel__plot--inert {
  pointer-events: none;
}

.graphing-graph-panel__empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 100%;
  margin: 0;
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
