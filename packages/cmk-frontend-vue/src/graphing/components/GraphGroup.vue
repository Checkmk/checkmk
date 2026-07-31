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
import { useRequestedTimeRange } from '../composables/useRequestedTimeRange'
import type { RequestedTimeRange, TimeRangeCommitKind } from '../types'
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
    // Outer figure width in CSS pixels (plot area + axis margins); the RRD step
    // resolution is derived from the resulting plot width.
    figure_width?: number
  }>(),
  { combination_mode: null, figure_width: 800 }
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

const { graphs, isLoading, error } = useGraphData(
  () => props.graphs,
  () => requestedTimeRange.value,
  () => props.figure_width - CANVAS_MARGIN_HORIZONTAL,
  () => consolidationFn.value,
  () => props.combination_mode
)

const { graphs: overviewGraphs } = useGraphData(
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

// Only the visuals wait; aria-busy below is undelayed.
const showSkeletons = useDelayedFlag(() => isInitialLoad.value, LOADING_AFFORDANCE_DELAY_MS)

// Named because the resolved `graphs` above shadows `props.graphs` in the template.
const definitionCount = computed(() => props.graphs.length)
</script>

<template>
  <div class="graphing-graph-group" :aria-busy="isInitialLoad">
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
    <div v-else-if="error" class="graphing-graph-group__error">{{ error }}</div>
    <template v-else>
      <GraphPanel
        v-for="(graph, i) in graphs"
        :key="i"
        class="graphing-graph-group__panel"
        :metrics="graph.metrics"
        :data-time-range="graph.timeRange"
        :requested-time-range="requestedTimeRange"
        :title="graph.title"
        :show-title="true"
        :show-timestamp="true"
        :show-consolidation="true"
        :show-legend="true"
        :interaction="props.graphs[i]!.interaction"
        :overview="overviews[i]"
        :horizontal-lines="graph.horizontalLines"
        :figure-width="figure_width"
        :add-to="graph?.addTo"
        @update:requested-time-range="onPanelTimeRange"
        @update:consolidation-fn="consolidationFn = $event"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-group {
  display: flex;
  flex-direction: column;
  gap: calc(var(--spacing) * 4);
}

.graphing-graph-group__error {
  padding: calc(var(--spacing) * 2);
  color: var(--font-color);
}

.graphing-graph-group__error {
  color: var(--color-state-crit-background);
}
</style>
