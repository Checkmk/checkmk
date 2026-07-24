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
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { useBrushCoordination } from '../composables/useBrushCoordination'
import { type GraphCombinationMode, useGraphData } from '../composables/useGraphData'
import { useRequestedTimeRange } from '../composables/useRequestedTimeRange'
import type { RequestedTimeRange, TimeRangeCommitKind } from '../types'
import GraphPanel from './GraphPanel.vue'
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
</script>

<template>
  <div class="graphing-graph-group">
    <!--
      Only the very first load (no graphs yet) shows the full placeholder. A refetch
      triggered later (zoom, pan, brush, global picker) must not unmount the panels below.
    -->
    <div v-if="isLoading && graphs.length === 0" class="graphing-graph-group__loading">
      {{ _t('Loading graphs…') }}
    </div>
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
        :show-legend="true"
        :show-brush="true"
        :overview="overviews[i]"
        :horizontal-lines="graph.horizontalLines"
        :figure-width="figure_width"
        :add-type="graph?.addType"
        :internal="graph?.internal"
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

.graphing-graph-group__loading,
.graphing-graph-group__error {
  padding: calc(var(--spacing) * 2);
  color: var(--font-color);
}

.graphing-graph-group__error {
  color: var(--color-state-crit-background);
}
</style>
