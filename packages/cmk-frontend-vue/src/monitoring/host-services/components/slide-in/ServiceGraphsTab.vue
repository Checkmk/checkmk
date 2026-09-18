<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'

import type { DiscoveredGraph } from '@/monitoring/host-services/api/graphs'

export interface ServiceGraphs {
  graphs: DiscoveredGraph[]
  /** Why the service has no graphs, in the backend's words. Null when it has some. */
  noDataMessage: string | null
  /** The legacy page holding the same graphs. */
  graphsLink: string
}

const PANEL_GRAPH_HEIGHT = 300

// The panel is its own world: a graph may be zoomed, panned and read, but not pinned to a page
// that is not there, nor added to a visual from inside a slide-in.
const PANEL_INTERACTION: CmkTimeSeriesGraph['interaction'] = {
  burger: 'enabled',
  zoom: 'enabled',
  panning: 'enabled',
  hover: 'enabled',
  brush: 'enabled',
  pin: 'disabled'
}

export function toTimeSeriesGraph(shell: DiscoveredGraph, width: number): CmkTimeSeriesGraph {
  return {
    size: { width, height: PANEL_GRAPH_HEIGHT, mode: 'resizable' },
    options: {
      header: { title: shell.title, show_graph_time: true },
      name: shell.name,
      x_axis: null,
      y_axis: shell.y_axis,
      font_size_pt: 8
    },
    interaction: PANEL_INTERACTION,
    internal: shell.internal,
    add_to: null,
    time_range: null
  }
}
</script>

<script setup lang="ts">
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, onMounted, ref } from 'vue'

import { GraphGroup } from '@/graphing'

const props = defineProps<{ data: ServiceGraphs }>()

const { _t } = usei18n()

const DAYS_SHOWN = 8
const SECONDS_PER_DAY = 24 * 60 * 60

// The panel sizes its own graphs: GraphGroup measures the page's content area when left to
// itself, which is the listing behind this panel rather than the panel.
const containerEl = ref<HTMLElement | null>(null)
const containerWidth = ref(0)

const { observe } = useResizeObserver((entries) => {
  const entry = entries[0]
  if (entry) {
    containerWidth.value = entry.contentRect.width
  }
})
observe(containerEl)

// The observer's first delivery is async, so the graphs would wait a frame for a width.
onMounted(() => {
  containerWidth.value = containerEl.value?.getBoundingClientRect().width ?? 0
})

const timeRange = computed(() => {
  const end = Math.floor(Date.now() / 1000)
  return { start: end - DAYS_SHOWN * SECONDS_PER_DAY, end }
})

const graphHeight = PANEL_GRAPH_HEIGHT

const graphs = computed(() =>
  props.data.graphs.map((shell) => toTimeSeriesGraph(shell, containerWidth.value))
)
</script>

<template>
  <div ref="containerEl" class="monitoring-service-graphs-tab">
    <CmkLink class="monitoring-service-graphs-tab__link" :href="data.graphsLink" target="_top">
      <CmkIcon name="graph" size="small" />
      {{ _t('Open the service graph page') }}
    </CmkLink>
    <div v-if="graphs.length === 0" class="monitoring-service-graphs-tab__empty">
      <CmkParagraph v-if="data.noDataMessage === null">
        {{ _t('Checkmk has no graphs for this service.') }}
      </CmkParagraph>
      <CmkHtml v-else :html="data.noDataMessage" />
    </div>
    <GraphGroup
      v-else-if="containerWidth > 0"
      :graphs="graphs"
      :figure_width="containerWidth"
      :figure_height="graphHeight"
      :initial_time_range_start="timeRange.start"
      :initial_time_range_end="timeRange.end"
      time_range_scope="local"
    />
  </div>
</template>

<style scoped>
.monitoring-service-graphs-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-service-graphs-tab__empty {
  color: var(--font-color-dimmed);
}

.monitoring-service-graphs-tab__link {
  align-self: flex-end;
  align-items: center;
  width: auto;
}
</style>
