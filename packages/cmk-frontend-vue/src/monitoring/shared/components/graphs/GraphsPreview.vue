<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import { type GraphDisplayOptions, GraphGroup, GraphSkeleton } from '@/graphing'
import { type DiscoveredGraphs, GraphsApi, toTimeSeriesGraph } from '@/monitoring/shared/api/graphs'
import type { HostRef } from '@/monitoring/shared/api/types'

import GraphsNoData from './GraphsNoData.vue'

const props = defineProps<{
  host: HostRef
  /** The service to preview the graphs of. Omitted for the graphs of the host itself. */
  service?: string | undefined
}>()

const { _t } = usei18n()

// The size and time window of the legacy views' hover graphs, so both previews read alike.
const FIGURE_WIDTH = 330
const FIGURE_HEIGHT = 110
const HOURS_SHOWN = 8
const SECONDS_PER_HOUR = 60 * 60

// What a graph takes of the preview's width: the figure, and the border GraphPanel draws on either
// side of a hover graph. The style fits whole columns of it into the room the tooltip has.
const PANEL_BORDER = 1
const PANEL_WIDTH = `${FIGURE_WIDTH + 2 * PANEL_BORDER}px`

const PREVIEW_SIZE: CmkTimeSeriesGraph['size'] = {
  width: FIGURE_WIDTH,
  height: FIGURE_HEIGHT,
  mode: 'fixed'
}

// A preview is only looked at: whatever it offers to do goes away with the pointer.
const PREVIEW_INTERACTION: CmkTimeSeriesGraph['interaction'] = {
  burger: 'disabled',
  zoom: 'disabled',
  panning: 'disabled',
  hover: 'disabled',
  brush: 'disabled',
  pin: 'disabled'
}

const PREVIEW_DISPLAY: GraphDisplayOptions = {
  show_consolidation: false,
  show_legend: false,
  show_title: true,
  show_vertical_axis: true,
  show_time_axis: true
}

const graphsApi = new GraphsApi()

const discovered = ref<DiscoveredGraphs | null>(null)
const failed = ref(false)

onMounted(async () => {
  try {
    discovered.value = await graphsApi.discover(props.host, props.service)
  } catch {
    failed.value = true
  }
})

const timeRange = computed(() => {
  const end = Math.floor(Date.now() / 1000)
  return { start: end - HOURS_SHOWN * SECONDS_PER_HOUR, end }
})

const graphs = computed(
  () =>
    discovered.value?.graphs.map((graph) =>
      toTimeSeriesGraph(graph, PREVIEW_SIZE, PREVIEW_INTERACTION)
    ) ?? []
)
</script>

<template>
  <div class="monitoring-graphs-preview">
    <CmkAlert v-if="failed" variant="error" :text="_t('The graphs could not be loaded.')" />
    <GraphSkeleton
      v-else-if="discovered === null"
      :figure-width="FIGURE_WIDTH"
      :figure-height="FIGURE_HEIGHT"
      :show-legend="false"
      :show-brush="false"
    />
    <CmkAlert
      v-else-if="discovered.errorMessage !== null"
      variant="error"
      :text="untranslated(discovered.errorMessage)"
    />
    <GraphsNoData
      v-else-if="graphs.length === 0"
      :subject="service === undefined ? 'host' : 'service'"
      :message="discovered.noDataMessage"
    />
    <GraphGroup
      v-else
      :graphs="graphs"
      :figure_width="FIGURE_WIDTH"
      :figure_height="FIGURE_HEIGHT"
      :initial_time_range_start="timeRange.start"
      :initial_time_range_end="timeRange.end"
      :display="PREVIEW_DISPLAY"
      layout="wrap"
      time_range_scope="local"
    />
  </div>
</template>

<style scoped>
/* Four graphs side by side at most, as the legacy hover shows them, and fewer when the room beside
   the icon is narrower, so the graphs wrap into more rows instead of leaving the screen. The room
   is what the tooltip has on the side it opened to, less its own padding and border. It is cut
   down to whole columns: once the graphs wrap, the box takes its maximum width, and any part of a
   column left in it would stay empty beside the graphs. A room narrower than a single graph keeps
   the box within it, to scroll the graph sideways. */
.monitoring-graphs-preview {
  --monitoring-graphs-preview-frame: calc(2 * var(--dimension-4) + 2px);
  --monitoring-graphs-preview-room: calc(
    var(--reka-tooltip-content-available-width, 100vw) - var(--monitoring-graphs-preview-frame)
  );

  /* The gap GraphGroup leaves between the graphs it wraps. */
  --monitoring-graphs-preview-gap: 2px;
  --monitoring-graphs-preview-column: calc(
    v-bind(PANEL_WIDTH) + var(--monitoring-graphs-preview-gap)
  );

  width: max-content;
  max-width: min(
    var(--monitoring-graphs-preview-room),
    calc(
      clamp(
          var(--monitoring-graphs-preview-column),
          round(
            down,
            var(--monitoring-graphs-preview-room) + var(--monitoring-graphs-preview-gap),
            var(--monitoring-graphs-preview-column)
          ),
          4 * var(--monitoring-graphs-preview-column)
        ) -
        var(--monitoring-graphs-preview-gap)
    )
  );
  max-height: calc(
    var(--reka-tooltip-content-available-height, 100vh) - var(--monitoring-graphs-preview-frame)
  );
  overflow: auto;
}

/* Opened to the left of the icon, the rows keep to the icon, as the legacy hover's do. */
[data-side='left'] .monitoring-graphs-preview {
  --cmk-graph-group-justify-content: flex-end;
}
</style>
