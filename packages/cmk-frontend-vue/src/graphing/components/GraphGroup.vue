<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<!--
Entry-point component for rendering a group of graphs fetched from the REST API.
Registered as the cmk-graph-group custom element via defineCmkComponent in main.ts.
-->

<script setup lang="ts">
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import CmkVisuallyHidden from 'cmk-ui-library/components/CmkVisuallyHidden.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type ComponentPublicInstance, computed, onMounted, ref, watch } from 'vue'

import { useGlobalRefresh } from '../GlobalTimePicker/globalTimeState'
import { useBrushSnapshot } from '../composables/useBrushSnapshot'
import { type GraphCombinationMode, useGraphData } from '../composables/useGraphData'
import { useGraphNotice } from '../composables/useGraphNotice'
import { useLocalTimeRange } from '../composables/useLocalTimeRange'
import { useRequestedTimeRange } from '../composables/useRequestedTimeRange'
import type { BrushOverview, RequestedTimeRange, TimeRangeCommitKind } from '../types'
import { drawnTimeRange } from '../utils/timeRange'
import GraphNotice from './GraphNotice.vue'
import GraphPanel from './GraphPanel.vue'
import GraphSkeleton from './GraphSkeleton.vue'
import { type ConsolidationFn, DEFAULT_CONSOLIDATION_FN } from './consolidation'
import { CANVAS_MARGIN_HORIZONTAL } from './constants'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    initial_time_range_start: number
    initial_time_range_end: number
    graphs: CmkTimeSeriesGraph[]
    // How a combined graph folds the same metric across its matched services;
    // null for graph types without a combination (e.g. template graphs).
    combination_mode?: GraphCombinationMode | null
    // Outer figure width in CSS pixels (plot area + axis margins); the RRD step resolution is
    // derived from the resulting plot width. absent means "fill the available page width"
    // - see effectiveWidth below.
    figure_width?: number
    figure_height?: number
    show_consolidation?: boolean
    show_legend?: boolean
    // 'column' stacks the panels vertically (the default)
    // 'wrap' flows the fixed-width panels into as many columns as the container allows
    layout?: 'column' | 'wrap'
    // 'global' follows the page's global time picker, and publishes the group's own zooms and
    // pans back to it (the default)
    // 'local' keeps the range to this group alone, for an embed that must not steer the page
    // it sits on (a slide-in panel, say)
    time_range_scope?: 'global' | 'local'
  }>(),
  {
    combination_mode: null,
    figure_height: 300,
    show_consolidation: true,
    show_legend: true,
    layout: 'column',
    time_range_scope: 'global'
  }
)

const groupEl = ref<HTMLElement | null>(null)
const availableWidth = ref(0)

// Without figure_width the graphs fill the page, so the width comes from #main_page_content.
if (props.figure_width === undefined) {
  const containerEl = ref<HTMLElement | null>(null)

  const recomputeAvailableWidth = (): void => {
    const group = groupEl.value
    const container = containerEl.value
    if (!group || !container) {
      return
    }
    availableWidth.value = Math.max(
      0,
      container.getBoundingClientRect().right - group.getBoundingClientRect().left - 20
    )
  }

  const { observe } = useResizeObserver(recomputeAvailableWidth)
  observe(containerEl)

  onMounted(() => {
    containerEl.value = document.getElementById('main_page_content')
    recomputeAvailableWidth()
  })
}

const effectiveWidth = computed(() => props.figure_width ?? availableWidth.value)

// Seeded from the backend-provided initial range, then follows the page's global time picker;
// brush interactions, time zooms and pans on individual panels write to it directly, and that
// write is published back to the global time picker so other graphs/groups on the page follow.
// Unless the group was told to keep to itself, in which case the same writes stay here.
const initialTimeRange = {
  start: props.initial_time_range_start,
  end: props.initial_time_range_end
}
const { requestedTimeRange, setRequestedTimeRange, timePickerRequests } =
  props.time_range_scope === 'global'
    ? useRequestedTimeRange(initialTimeRange)
    : useLocalTimeRange(initialTimeRange)
const consolidationFnPerPanel = ref<ConsolidationFn[]>([])
const consolidationFnOfPanel = (panelIndex: number): ConsolidationFn =>
  consolidationFnPerPanel.value[panelIndex] ?? DEFAULT_CONSOLIDATION_FN

const { pauseRefresh } = useGlobalRefresh()

// One strip for the whole group — every panel shows the same range; only the series differ.
const brush = useBrushSnapshot<BrushOverview[]>({
  getNow: () => Math.floor(Date.now() / 1000),
  getRequestedTimeRange: () => requestedTimeRange.value
})

function onPanelTimeRange(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
  brush.onRangeCommitted(range, kind)
  setRequestedTimeRange(range)
}

const { graphs, isLoading, loadingSlots, error, partialErrors, warnings, reload } = useGraphData(
  () => props.graphs,
  () => requestedTimeRange.value,
  () => effectiveWidth.value - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFnPerPanel.value,
  () => props.combination_mode
)

const { graphs: overviewGraphs, reload: reloadOverview } = useGraphData(
  () => props.graphs,
  () => brush.requestedDomain.value,
  () => effectiveWidth.value - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFnPerPanel.value,
  () => props.combination_mode
)

// Derived from the response that fills it, never from `brush.requestedDomain`, which by now may
// have moved on: a strip snapped to one fetch's grid and drawn over another's series is what put
// the selection bar in the wrong place.
watch(overviewGraphs, (graphs) => {
  const answered = graphs[0]
  if (answered === undefined) {
    return
  }
  brush.onOverviewFetched({
    requestedDomain: answered.requestedTimeRange,
    drawnDomain: drawnTimeRange(answered.requestedTimeRange, answered.timeRange),
    data: graphs.map((graph) => ({ metrics: graph.metrics, dataTimeRange: graph.timeRange }))
  })
})

function brushSnapshotOf(panelIndex: number) {
  const snapshot = brush.snapshot.value
  const overview = snapshot?.data[panelIndex]
  return snapshot && overview ? { ...snapshot, data: overview } : undefined
}

// A refetch is skeletonised too: the curves still on screen are the previous range's, so leaving
// them up reads as nothing having happened. Only that case is worth delaying - a slot that has
// never held a graph has nothing to leave up, so its wait is blank rather than flickering.
// A failure is exempt either way, its notice occupies the area.
const delayHasElapsed = useDelayedFlag(
  () => loadingSlots.value.some(Boolean) && error.value === null,
  LOADING_AFFORDANCE_DELAY_MS
)

// One entry per graph definition, so a panel waiting on its own data is the only one replaced:
// a consolidation change refetches that panel alone, and blanking its neighbours would lose
// data they still hold.
const slots = computed(() =>
  Array.from({ length: props.graphs.length }, (_unused, index) => {
    const graph = graphs.value[index] ?? null
    const isWaiting = (loadingSlots.value[index] ?? false) && error.value === null
    return {
      index,
      graph,
      isAwaitingData: loadingSlots.value[index] ?? false,
      isSkeleton: isWaiting && (graph === null || delayHasElapsed.value)
    }
  })
)

const showSkeletons = computed(() => slots.value.some((slot) => slot.isSkeleton))

// Keyed by slot rather than collected in order: skeletons and panels interleave, so a ref array
// would not line up with the slots the heights are read back against.
const panelEls = new Map<number, HTMLElement>()

function registerPanel(index: number, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLElement) {
    panelEls.set(index, el)
  } else {
    panelEls.delete(index)
  }
}

// Read as the skeletons go up but before they render, so the panels they replace are still on
// screen and each skeleton can hold its own one's footprint.
const panelHeights = ref<(number | undefined)[]>([])

watch(showSkeletons, (showing) => {
  if (!showing) {
    return
  }
  panelHeights.value = slots.value.map(
    ({ index }) => panelEls.get(index)?.getBoundingClientRect().height
  )
})

const notice = useGraphNotice({
  error: () => error.value,
  isLoading: () => isLoading.value,
  partialErrors: () => partialErrors.value,
  warnings: () => warnings.value
})

// The overview feeds the brush below the plot, so a retry has to refresh it too.
function onRetry(): void {
  reload()
  reloadOverview()
}
</script>

<template>
  <div
    ref="groupEl"
    class="graphing-graph-group"
    :class="`graphing-graph-group--${layout}`"
    :aria-busy="isLoading"
  >
    <!-- The pills below repeat one message over every panel, so they stay silent and the group
         announces it once here. -->
    <CmkVisuallyHidden v-if="showSkeletons" :text="_t('Loading graphs…')" live="polite" />
    <CmkVisuallyHidden
      v-else-if="notice"
      :text="notice.message"
      :live="notice.variant === 'error' ? 'assertive' : 'polite'"
    />
    <!-- A slot with neither yet is a first load still inside the delay, and stays blank. -->
    <template v-for="panelSlot in slots" :key="panelSlot.index">
      <GraphSkeleton
        v-if="panelSlot.isSkeleton"
        class="graphing-graph-group__panel"
        :figure-width="effectiveWidth"
        :figure-height="figure_height"
        :show-legend="show_legend"
        :show-brush="props.graphs[panelSlot.index]!.interaction.brush === 'enabled'"
        :height="panelHeights[panelSlot.index]"
      />
      <div
        v-else-if="panelSlot.graph"
        :ref="(el) => registerPanel(panelSlot.index, el)"
        class="graphing-graph-group__panel"
      >
        <GraphPanel
          :consolidation-fn="consolidationFnOfPanel(panelSlot.index)"
          :metrics="panelSlot.graph.metrics"
          :data-time-range="panelSlot.graph.timeRange"
          :requested-time-range="requestedTimeRange"
          :awaiting-data="panelSlot.isAwaitingData"
          :time-picker-requests="timePickerRequests"
          :y-axis="props.graphs[panelSlot.index]!.options.y_axis"
          :title="panelSlot.graph.title"
          :show-title="true"
          :show-timestamp="true"
          :show-consolidation="show_consolidation"
          :show-legend="show_legend"
          :interaction="props.graphs[panelSlot.index]!.interaction"
          :brush-snapshot="brushSnapshotOf(panelSlot.index)"
          :horizontal-lines="panelSlot.graph.horizontalLines"
          :figure-width="effectiveWidth"
          :figure-height="figure_height"
          :add-to="panelSlot.graph.addTo"
          :header-is-compact="layout === 'wrap'"
          @update:requested-time-range="onPanelTimeRange"
          @update:consolidation-fn="consolidationFnPerPanel[panelSlot.index] = $event"
          @inspect="pauseRefresh"
        />
        <GraphNotice
          v-if="notice"
          v-bind="notice"
          silent
          class="graphing-graph-group__notice"
          @retry="onRetry"
        />
      </div>
    </template>
    <!-- A first load that failed has no panel to sit over, so the notice stands on its own. -->
    <GraphNotice
      v-if="notice && graphs.length === 0"
      v-bind="notice"
      silent
      class="graphing-graph-group__notice--standalone"
      @retry="onRetry"
    />
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-group {
  display: flex;
}

.graphing-graph-group--column {
  flex-direction: column;
  gap: calc(var(--spacing) * 4);
}

// Fixed-width panels flow left-to-right and wrap into columns as the container width allows.
// A tight gap keeps the multi-column grid compact (matching the legacy per-graph 2px margins).
.graphing-graph-group--wrap {
  flex-flow: row wrap;
  align-items: flex-start;
  gap: 2px;
}

.graphing-graph-group__panel {
  position: relative;
}

// Centred on the panel, not on its plot alone: the plot's box is GraphPanel's own business.
.graphing-graph-group__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.graphing-graph-group__notice--standalone {
  align-self: center;
}
</style>
