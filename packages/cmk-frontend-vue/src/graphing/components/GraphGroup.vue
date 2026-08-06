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
import { computed, ref, watch } from 'vue'

import { useBrushCoordination } from '../composables/useBrushCoordination'
import { type GraphCombinationMode, useGraphData } from '../composables/useGraphData'
import { useGraphNotice } from '../composables/useGraphNotice'
import { useRequestedTimeRange } from '../composables/useRequestedTimeRange'
import type { RequestedTimeRange, TimeRangeCommitKind } from '../types'
import GraphNotice from './GraphNotice.vue'
import GraphPanel from './GraphPanel.vue'
import GraphSkeleton from './GraphSkeleton.vue'
import type { ConsolidationFn } from './consolidation'
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
    // Outer figure dimensions in CSS pixels (plot area + axis margins); the RRD step
    // resolution is derived from the resulting plot width. Defaulted so they are always
    // concrete numbers when forwarded to the panel.
    figure_width?: number
    figure_height?: number
    show_consolidation?: boolean
    show_legend?: boolean
    // 'column' stacks the panels vertically (the default)
    // 'wrap' flows the fixed-width panels into as many columns as the container allows
    layout?: 'column' | 'wrap'
  }>(),
  {
    combination_mode: null,
    figure_width: 800,
    figure_height: 300,
    show_consolidation: true,
    show_legend: true,
    layout: 'column'
  }
)

// Seeded from the backend-provided initial range, then follows the page's global time picker;
// brush interactions, time zooms and pans on individual panels write to it directly, and that
// write is published back to the global time picker so other graphs/groups on the page follow.
const requestedTimeRange = useRequestedTimeRange({
  start: props.initial_time_range_start,
  end: props.initial_time_range_end
})
const consolidationFn = ref<ConsolidationFn>('avg')

const brushCoordination = useBrushCoordination(
  () => Math.floor(Date.now() / 1000),
  requestedTimeRange.value
)

function onPanelTimeRange(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
  brushCoordination.onBrushChange(range, kind)
  requestedTimeRange.value = range
}

watch(requestedTimeRange, (range) => {
  const known = brushCoordination.graphRange.value
  if (range.start !== known.start || range.end !== known.end) {
    brushCoordination.onExternalRange(range)
  }
})

const { graphs, isLoading, error, partialErrors, warnings, reload } = useGraphData(
  () => props.graphs,
  () => requestedTimeRange.value,
  () => props.figure_width - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFn.value,
  () => props.combination_mode
)

const { graphs: overviewGraphs, reload: reloadOverview } = useGraphData(
  () => props.graphs,
  () => brushCoordination.brushDomain.value,
  () => props.figure_width - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFn.value,
  () => props.combination_mode
)
const overviews = computed(() =>
  overviewGraphs.value.map((graph) => ({ metrics: graph.metrics, timeRange: graph.timeRange }))
)

// A refetch (zoom, pan, brush, global picker) keeps the panels rendered, so it is not an initial
// load. Both the skeletons and aria-busy key off this rather than off `isLoading`.
const isInitialLoad = computed(() => isLoading.value && graphs.value.length === 0)

// Only the visuals wait; aria-busy below is undelayed. The skeleton also stands down for a failure,
// which already occupies the area with its own notice.
const showSkeletons = useDelayedFlag(
  () => isInitialLoad.value && error.value === null,
  LOADING_AFFORDANCE_DELAY_MS
)

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

// Named because the resolved `graphs` above shadows `props.graphs` in the template.
const definitionCount = computed(() => props.graphs.length)
</script>

<template>
  <div
    class="graphing-graph-group"
    :class="`graphing-graph-group--${layout}`"
    :aria-busy="isInitialLoad"
  >
    <!-- Until the delay elapses no branch matches and no panels exist yet, leaving the area blank. -->
    <template v-if="showSkeletons">
      <CmkVisuallyHidden :text="_t('Loading graphs…')" live="polite" />
      <GraphSkeleton
        v-for="n in definitionCount"
        :key="n"
        class="graphing-graph-group__panel"
        :figure-width="figure_width"
      />
    </template>
    <template v-else>
      <!-- The pills below repeat one message over every panel, so they stay silent and the group
           announces it once here. -->
      <CmkVisuallyHidden
        v-if="notice"
        :text="notice.message"
        :live="notice.variant === 'error' ? 'assertive' : 'polite'"
      />
      <div v-for="(graph, i) in graphs" :key="i" class="graphing-graph-group__panel">
        <GraphPanel
          :metrics="graph.metrics"
          :data-time-range="graph.timeRange"
          :requested-time-range="requestedTimeRange"
          :title="graph.title"
          :show-title="true"
          :show-timestamp="true"
          :show-consolidation="show_consolidation"
          :show-legend="show_legend"
          :interaction="props.graphs[i]!.interaction"
          :overview="overviews[i]"
          :horizontal-lines="graph.horizontalLines"
          :figure-width="figure_width"
          :figure-height="figure_height"
          :add-to="graph?.addTo"
          @update:requested-time-range="onPanelTimeRange"
          @update:consolidation-fn="consolidationFn = $event"
        />
        <GraphNotice
          v-if="notice"
          v-bind="notice"
          silent
          class="graphing-graph-group__notice"
          @retry="onRetry"
        />
      </div>
      <!-- A first load that failed has no panel to sit over, so the notice stands on its own. -->
      <GraphNotice
        v-if="notice && graphs.length === 0"
        v-bind="notice"
        silent
        class="graphing-graph-group__notice--standalone"
        @retry="onRetry"
      />
    </template>
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
