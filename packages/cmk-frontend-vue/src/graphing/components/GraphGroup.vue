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
import CmkSurfaceNotice, {
  type CmkSurfaceNoticeVariant
} from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import CmkVisuallyHidden from 'cmk-ui-library/components/CmkVisuallyHidden.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { computed, onMounted, ref, watch } from 'vue'

import { useGlobalRefresh } from '../GlobalTimePicker/globalTimeState'
import { useBrushSnapshot } from '../composables/useBrushSnapshot'
import {
  type GraphCombinationMode,
  type GraphLoad,
  type ResolvedGraph,
  useGraphData
} from '../composables/useGraphData'
import {
  type GraphNoticeDescriptor,
  graphNoticeOf,
  hasPlottableData,
  useNoDataNotice
} from '../composables/useGraphNotice'
import { useLocalTimeRange } from '../composables/useLocalTimeRange'
import { useRequestedTimeRange } from '../composables/useRequestedTimeRange'
import { useSharedResizeObserver } from '../composables/useSharedResizeObserver'
import type {
  BrushOverview,
  GraphDisplayOptions,
  PanelKey,
  RequestedTimeRange,
  TimeRangeCommitKind
} from '../types'
import { drawnTimeRange, sameRequestedTimeRange } from '../utils/timeRange'
import GraphGroupEntry from './GraphGroupEntry.vue'
import GraphPanel from './GraphPanel.vue'
import { clippedToNavigableTime, navigableBounds } from './TimeSeriesGraph/interaction/timeBounds'
import { type ConsolidationFn, DEFAULT_CONSOLIDATION_FN } from './consolidation'
import { CANVAS_MARGIN_HORIZONTAL, MAX_FIGURE_WIDTH } from './constants'

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
    // derived from the resulting plot width. if absent we fill the available page width up until a
    // threshold of MAX_FIGURE_WIDTH - see effectiveWidth below.
    figure_width?: number
    figure_height?: number
    // Omit for the defaults below, or send the whole object.
    display?: GraphDisplayOptions
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
    display: () => ({
      show_consolidation: true,
      show_legend: true,
      show_title: true,
      show_vertical_axis: true,
      show_time_axis: true
    }),
    layout: 'column',
    time_range_scope: 'global'
  }
)

const groupEl = ref<HTMLElement | null>(null)
const availableWidth = ref(0)

function pixels(length: string): number {
  return parseFloat(length) || 0
}

function contentRightEdge(element: HTMLElement): number {
  const style = getComputedStyle(element)
  const borderRight = pixels(style.borderRightWidth)
  const scrollbarWidth = Math.max(
    0,
    element.offsetWidth - element.clientLeft - element.clientWidth - borderRight
  )
  return (
    element.getBoundingClientRect().right -
    borderRight -
    scrollbarWidth -
    pixels(style.paddingRight)
  )
}

// The panels' padding sits inside the group, out of reach of rightInsetWithin, so the figures
// and the skeletons that stand in for them give it up themselves.
function panelPadding(group: HTMLElement): number {
  return pixels(getComputedStyle(group).getPropertyValue('--graphing-graph-group-panel-padding'))
}

function rightInsetWithin(descendant: HTMLElement, ancestor: HTMLElement): number {
  let inset = 0
  for (
    let element = descendant.parentElement;
    element && element !== ancestor;
    element = element.parentElement
  ) {
    const style = getComputedStyle(element)

    // Ignore elements that do not actually render insets
    if (style.display === 'contents') {
      continue
    }
    const collapsedTable = style.display === 'table' && style.borderCollapse === 'collapse'

    inset +=
      (collapsedTable ? 0 : pixels(style.paddingRight)) +
      pixels(style.borderRightWidth) +
      pixels(style.marginRight)
  }
  return inset
}

// Without figure_width the graphs fill the page, so the width comes from #main_page_content or
// #dashlet_content_wrapper as a fallback for view widget rendering (iframe, no #main_page_content)
// or the document element as last fallback.
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
      contentRightEdge(container) -
        group.getBoundingClientRect().left -
        rightInsetWithin(group, container) -
        2 * panelPadding(group)
    )
  }

  useSharedResizeObserver(containerEl, recomputeAvailableWidth)

  onMounted(() => {
    containerEl.value =
      document.getElementById('main_page_content') ??
      document.getElementById('dashlet_content_wrapper') ?? // within view widgets
      document.documentElement
    recomputeAvailableWidth()
  })
}

const effectiveWidth = computed(
  () => props.figure_width ?? Math.min(MAX_FIGURE_WIDTH, availableWidth.value)
)

// Seeded from the backend-provided initial range, then follows the page's global time picker;
// brush interactions, time zooms and pans on individual panels write to it directly, and that
// write is published back to the global time picker so other graphs/groups on the page follow.
// Unless the group was told to keep to itself, in which case the same writes stay here.
const initialTimeRange = {
  start: props.initial_time_range_start,
  end: props.initial_time_range_end
}
const { requestedTimeRange, setRequestedTimeRange, rangeChange } =
  props.time_range_scope === 'global'
    ? useRequestedTimeRange(initialTimeRange)
    : useLocalTimeRange(initialTimeRange)
const consolidationFnPerPanel = ref<ConsolidationFn[]>([])
const consolidationFnOfPanel = (panelIndex: number): ConsolidationFn =>
  consolidationFnPerPanel.value[panelIndex] ?? DEFAULT_CONSOLIDATION_FN

const { pauseRefresh } = useGlobalRefresh()

// One strip for the whole group — every panel shows the same range; only the series differ.
const brush = useBrushSnapshot<(BrushOverview | null)[]>({
  getNow: () => Math.floor(Date.now() / 1000),
  getRequestedTimeRange: () => requestedTimeRange.value
})

function onPanelTimeRange(
  requested: RequestedTimeRange,
  kind: TimeRangeCommitKind,
  panelKey: PanelKey
): void {
  const range = clippedToNavigableTime(requested, navigableBounds())
  brush.onRangeCommitted(range, kind)
  setRequestedTimeRange(range, panelKey)
}

const nearView = ref<boolean[]>([])
const isWanted = (index: number): boolean => nearView.value[index] ?? false

const { loads, reload } = useGraphData(
  () => props.graphs,
  () => requestedTimeRange.value,
  () => effectiveWidth.value - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFnPerPanel.value,
  () => props.combination_mode,
  { isWanted }
)

const overviewGraphDefinitions = computed(() =>
  props.graphs.some((graph) => graph.interaction.brush === 'enabled') ? props.graphs : []
)

const { loads: overviewLoads, reload: reloadOverview } = useGraphData(
  () => overviewGraphDefinitions.value,
  () => brush.requestedDomain.value,
  () => effectiveWidth.value - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFnPerPanel.value,
  () => props.combination_mode,
  { getFetchBounds: navigableBounds, isWanted }
)

// Published once no strip is loading, so that the strips near the view switch together. Derived
// from the first strip that answers the current domain: a strip snapped to one fetch's grid and
// drawn over another's series is what put the selection bar in the wrong place. A strip without
// such an answer keeps its last one, which the brush draws at its own time range.
watch(overviewLoads, (overviews) => {
  if (overviews.some((overview) => overview.isLoading)) {
    return
  }
  const answered = overviews
    .map(({ graph }) => graph)
    .find(
      (graph): graph is ResolvedGraph =>
        graph !== null &&
        sameRequestedTimeRange(graph.requestedTimeRange, brush.requestedDomain.value)
    )
  if (answered === undefined) {
    return
  }
  brush.onOverviewFetched({
    requestedDomain: answered.requestedTimeRange,
    drawnDomain: clippedToNavigableTime(
      drawnTimeRange(answered.requestedTimeRange, answered.timeRange),
      navigableBounds()
    ),
    data: overviews.map(({ graph }) =>
      graph === null ? null : { metrics: graph.metrics, dataTimeRange: graph.timeRange }
    )
  })
})

const brushSnapshots = computed(() => {
  const snapshot = brush.snapshot.value
  return props.graphs.map((_graph, index) => {
    const overview = snapshot?.data[index]
    return snapshot && overview ? { ...snapshot, data: overview } : undefined
  })
})

const noDataNotice = useNoDataNotice()

// The fetch's own notice outranks a panel's emptiness, and a panel awaiting data is still showing
// the answer to the request before this one.
function noticeOf(load: GraphLoad): GraphNoticeDescriptor | null {
  const fetchNotice = graphNoticeOf(load)
  if (fetchNotice !== null) {
    return fetchNotice
  }
  return load.graph !== null && !load.isLoading && !hasPlottableData(load.graph.metrics)
    ? noDataNotice
    : null
}

// One entry per graph definition, so a panel waiting on its own data is the only one replaced:
// a consolidation change refetches that panel alone, and blanking its neighbours would lose
// data they still hold.
const entries = computed(() =>
  props.graphs.map((definition, index) => {
    const load = loads.value[index]!
    return { index, definition, load, notice: noticeOf(load) }
  })
)

const isLoading = computed(() => loads.value.some((load) => load.isLoading))

// The skeletons are aria-hidden, so the group announces the wait of each graph that shows one: a
// first load at once, a refetch once it outlasts the delay.
const refetchDelayHasElapsed = useDelayedFlag(
  () => loads.value.some((load) => load.isLoading && load.error === null),
  LOADING_AFFORDANCE_DELAY_MS
)
const announcesLoading = computed(() =>
  loads.value.some(
    (load) =>
      load.isLoading && load.error === null && (load.graph === null || refetchDelayHasElapsed.value)
  )
)

const NOTICE_SEVERITY: readonly CmkSurfaceNoticeVariant[] = ['error', 'warning', 'loading', 'info']

// The pills stay silent, so the group announces the most severe notice of its graphs.
const announcedNotice = computed(() => {
  const notices = entries.value.map(({ notice }) => notice)
  for (const variant of NOTICE_SEVERITY) {
    const notice = notices.find((each) => each?.variant === variant)
    if (notice) {
      return notice
    }
  }
  return null
})

// The overview feeds the brush below the plot, so a retry has to refresh it too.
function onRetry(index: number): void {
  reload(index)
  reloadOverview(index)
}
</script>

<template>
  <div
    ref="groupEl"
    class="graphing-graph-group"
    :class="`graphing-graph-group--${layout}`"
    :aria-busy="isLoading"
  >
    <!-- The pills below stay silent, so the group announces one message for all of them here. -->
    <CmkVisuallyHidden v-if="announcesLoading" :text="_t('Loading graphs…')" live="polite" />
    <CmkVisuallyHidden
      v-else-if="announcedNotice"
      :text="announcedNotice.message"
      :live="announcedNotice.variant === 'error' ? 'assertive' : 'polite'"
    />
    <GraphGroupEntry
      v-for="entry in entries"
      :key="entry.index"
      :load="entry.load"
      :notice="entry.notice"
      :figure-width="effectiveWidth"
      :figure-height="figure_height"
      :show-legend="display.show_legend"
      :show-brush="entry.definition.interaction.brush === 'enabled'"
      @near-view="nearView[entry.index] = $event"
      @retry="onRetry(entry.index)"
    >
      <template #panel="{ graph }">
        <GraphPanel
          :consolidation-fn="consolidationFnOfPanel(entry.index)"
          :metrics="graph.metrics"
          :data-time-range="graph.timeRange"
          :requested-time-range="requestedTimeRange"
          :awaiting-data="entry.load.isLoading"
          :panel-key="entry.index"
          :range-change="rangeChange"
          :y-axis="entry.definition.options.y_axis"
          :title="graph.title"
          :show-title="display.show_title"
          :show-timestamp="entry.definition.options.header.show_graph_time ?? true"
          :show-consolidation="display.show_consolidation"
          :show-legend="display.show_legend"
          :show-value-axis="display.show_vertical_axis"
          :show-time-axis="display.show_time_axis"
          :min-value-axis-width="display.min_value_axis_width"
          :interaction="entry.definition.interaction"
          :brush-snapshot="brushSnapshots[entry.index]"
          :horizontal-lines="graph.horizontalLines"
          :shaded-regions="graph.shadedRegions"
          :figure-width="effectiveWidth"
          :figure-height="figure_height"
          :add-to="graph.addTo"
          :is-hover-graph="layout === 'wrap'"
          @update:requested-time-range="(range, kind) => onPanelTimeRange(range, kind, entry.index)"
          @update:consolidation-fn="consolidationFnPerPanel[entry.index] = $event"
          @inspect="pauseRefresh"
        >
          <template #notice>
            <CmkSurfaceNotice
              v-if="entry.notice"
              v-bind="entry.notice"
              silent
              class="graphing-graph-group__notice"
              @retry="onRetry(entry.index)"
            />
          </template>
        </GraphPanel>
      </template>
    </GraphGroupEntry>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-group {
  display: flex;
}

// Panels keep their own width, not the group's, so a panel box ends where its capped graph does.
.graphing-graph-group--column {
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-7);
}

// Fixed-width panels flow left-to-right and wrap into columns as the container width allows.
// A tight gap keeps the multi-column grid compact (matching the legacy per-graph 2px margins).
.graphing-graph-group--wrap {
  flex-flow: row wrap;
  align-items: flex-start;
  gap: 2px;
  // --cmk-graph-group-justify-content is set by hover graph popups: cmk-frontend's hover.ts and
  // the monitoring pages' GraphsPreview. When a popup renders to the left of the cursor or icon,
  // this prevents a gap between it and the graph group.
  justify-content: var(--cmk-graph-group-justify-content, flex-start);
}

// Centred on the panel, not on its plot alone: the plot's box is GraphPanel's own business.
.graphing-graph-group__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
</style>
