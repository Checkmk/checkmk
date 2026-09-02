<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { staticAssertNever } from 'cmk-ui-library/lib/typeUtils'
import { computed, onMounted, ref, watch } from 'vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useInjectSharedWidgetGraphs } from '@/dashboard/composables/useSharedWidgetGraphs'
import type {
  AverageScatterplotContent,
  CombinedGraphContent,
  CustomGraphContent,
  PerformanceGraphContent,
  ProblemGraphContent,
  SingleTimeseriesContent
} from '@/dashboard/types/widget.ts'
import { GraphFigure } from '@/graphing'

import DashboardContentContainer from './DashboardContentContainer.vue'
import { createSharedGraphFetcher } from './sharedGraphFetcher.ts'
import type { ContentProps } from './types.ts'

type DiscoveredGraph = components['schemas']['ApiDiscoveredGraph']

const { _t } = usei18n()
const props =
  defineProps<
    ContentProps<
      | PerformanceGraphContent
      | SingleTimeseriesContent
      | CombinedGraphContent
      | AverageScatterplotContent
      | ProblemGraphContent
      | CustomGraphContent
    >
  >()

const shell = ref<DiscoveredGraph | null>(null)
const errorMessage = ref<string | null>(null)
const noDataMessage = ref<string | null>(null)
const isDiscovering = ref<boolean>(true)

// A shared dashboard authenticates by token: its filter values never reach the browser, so the
// backend discovers the shells at page render and the data is fetched per widget instead.
const cmkToken = useInjectCmkToken()
const sharedWidgetGraphs = useInjectSharedWidgetGraphs()
const fetchGraph = computed(() =>
  cmkToken === undefined ? undefined : createSharedGraphFetcher(props.widget_id, cmkToken)
)

const singleContext = computed(() => {
  const filters = props.effective_filter_context.filters
  return {
    host: filters['host']?.['host'] ?? null,
    service: filters['service']?.['service'] ?? null,
    site: filters['site']?.['site'] ?? null
  }
})

// Latest-wins: discard responses of superseded requests.
let requestCounter = 0

// Mirrors the legacy SingleTimeseriesDashlet._metric_color mapping.
const DEFAULT_THEME_COLOR = '#008EFF'

const PX_PER_PT = 96 / 72
const FIXED_VALUE_AXIS_WIDTH_IN_FONT_SIZES = 6
const DEFAULT_FONT_SIZE_PT = 8

const resolveTimeseriesColor = (color: SingleTimeseriesContent['color']): string | null => {
  if (color === 'default_metric') {
    return null
  }
  return color === 'default_theme' ? DEFAULT_THEME_COLOR : color
}

const resolveScatterplotColor = (
  color: AverageScatterplotContent['metric_color']
): string | null => {
  return color === 'default' ? null : color
}

type GraphDiscovery =
  | { graphs: DiscoveredGraph[]; no_data_message?: string | null }
  | { error: string }

const discoverGraphs = async (): Promise<GraphDiscovery> => {
  const content = props.content
  const { host, service, site } = singleContext.value
  switch (content.type) {
    case 'single_timeseries':
      if (host === null || service === null) {
        return { error: _t('Missing needed host and service parameters.') }
      }
      return unwrap(
        await client.POST('/domain-types/graph/actions/discover_single_timeseries_graphs/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            hostname: host,
            service_description: service,
            metric: content.metric,
            color: resolveTimeseriesColor(content.color)
          }
        })
      )
    case 'performance_graph':
      if (host === null || service === null) {
        return { error: _t('Missing needed host and service parameters.') }
      }
      // A numeric source is a pre-2.0 1-based index that cannot be resolved here.
      if (typeof content.source === 'number') {
        return {
          error: _t(
            'This widget references its graph by a deprecated index. Please edit the widget and re-select the graph.'
          )
        }
      }
      return unwrap(
        await client.POST('/domain-types/graph/actions/discover_template_graphs/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            hostname: host,
            service_description: service,
            site,
            graph_id: content.source
          }
        })
      )
    case 'combined_graph':
      return unwrap(
        await client.POST('/domain-types/graph/actions/discover_combined_graphs/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            context: props.effective_filter_context.filters,
            graph_id: content.graph_template
          }
        })
      )
    case 'average_scatterplot':
      return unwrap(
        await client.POST(
          '/domain-types/graph/actions/discover_average_scatterplot_graphs/invoke',
          {
            params: { header: { 'Content-Type': 'application/json' } },
            body: {
              context: props.effective_filter_context.filters,
              metric: content.metric,
              metric_color: resolveScatterplotColor(content.metric_color),
              average_color: resolveScatterplotColor(content.average_color),
              median_color: resolveScatterplotColor(content.median_color)
            }
          }
        )
      )
    case 'problem_graph':
      return unwrap(
        await client.POST('/domain-types/graph/actions/discover_problem_percentage_graphs/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            context: props.effective_filter_context.filters
          }
        })
      )
    case 'custom_graph':
      // A custom graph carries its own data sources (including their filter contexts), so the
      // dashboard's filter context does not take part in its discovery.
      return unwrap(
        await client.POST('/domain-types/graph/actions/discover_custom_graphs/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            custom_graph: content.custom_graph
          }
        })
      )
    default:
      staticAssertNever(content)
      return { graphs: [] }
  }
}

const applyDiscovery = (discovery: GraphDiscovery) => {
  if ('error' in discovery) {
    errorMessage.value = discovery.error
    noDataMessage.value = null
    shell.value = null
  } else if (discovery.graphs.length === 0) {
    // An empty discovery is an expected state (nothing matched / no monitored data),
    // not an error: show the backend's explanation rather than a failure box.
    noDataMessage.value = discovery.no_data_message || _t('No graph data available.')
    errorMessage.value = null
    shell.value = null
  } else {
    shell.value = discovery.graphs[0] ?? null
    errorMessage.value = null
    noDataMessage.value = null
  }
  isDiscovering.value = false
}

const loadGraph = async () => {
  const counter = ++requestCounter
  try {
    const discovery = await discoverGraphs()
    if (counter !== requestCounter) {
      return
    }
    applyDiscovery(discovery)
  } catch (error) {
    if (counter !== requestCounter) {
      return
    }
    errorMessage.value = `${_t('Failed to load graph:')} ${(error as Error).message}`
    noDataMessage.value = null
    shell.value = null
    isDiscovering.value = false
  }
}

const discoveryKey = computed(() => {
  const content = props.content
  switch (content.type) {
    case 'single_timeseries':
      return { metric: content.metric, color: content.color, context: singleContext.value }
    case 'performance_graph':
      return { source: content.source, context: singleContext.value }
    case 'combined_graph':
      return {
        graph_template: content.graph_template,
        context: props.effective_filter_context.filters
      }
    case 'average_scatterplot':
      return {
        metric: content.metric,
        colors: [content.metric_color, content.average_color, content.median_color],
        context: props.effective_filter_context.filters
      }
    case 'problem_graph':
      return { context: props.effective_filter_context.filters }
    case 'custom_graph':
      return { custom_graph: content.custom_graph }
    default:
      staticAssertNever(content)
      return {}
  }
})

// Pre-discovered shells are resolved once at page render, so nothing re-discovers them; the
// filters they were resolved from cannot change on a shared dashboard either.
if (sharedWidgetGraphs === undefined) {
  watch(
    () => JSON.stringify(discoveryKey.value),
    () => void loadGraph()
  )
}

// The figure-based average scatterplot has neither graph render options nor the graph
// contents' timerange field (its range lives in time_range).
const graphRenderOptions = computed(() => {
  const content = props.content
  return 'graph_render_options' in content ? content.graph_render_options : undefined
})
const timerange = computed(() => {
  const content = props.content
  return content.type === 'average_scatterplot' ? content.time_range : content.timerange
})
const showLegend = computed(() => graphRenderOptions.value?.show_legend ?? false)
const showTimestamp = computed(() => graphRenderOptions.value?.show_graph_time ?? false)
const showPin = computed(
  () => props.isPreview !== true && (graphRenderOptions.value?.show_pin ?? true)
)
const showTimeAxis = computed(() => graphRenderOptions.value?.show_time_axis ?? true)
const showValueAxis = computed(() => graphRenderOptions.value?.show_vertical_axis ?? true)
const showMargin = computed(() => graphRenderOptions.value?.show_margin ?? false)
const valueAxisWidth = computed(() => {
  const configuredWidth = graphRenderOptions.value?.vertical_axis_width
  if (typeof configuredWidth === 'number') {
    return configuredWidth * PX_PER_PT
  }
  const fontSizePt = graphRenderOptions.value?.font_size_pt ?? DEFAULT_FONT_SIZE_PT
  return FIXED_VALUE_AXIS_WIDTH_IN_FONT_SIZES * fontSizePt * PX_PER_PT
})
const combinationMode = computed(() => {
  const content = props.content
  return content.type === 'combined_graph' ? content.presentation : null
})

onMounted(() => {
  if (sharedWidgetGraphs === undefined) {
    void loadGraph()
    return
  }
  applyDiscovery(
    sharedWidgetGraphs[props.widget_id] ?? { error: _t('This graph could not be resolved.') }
  )
})
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
    :is-scrollable-preview="(isPreview ?? false) && showLegend"
  >
    <div
      class="db-content-time-series-graph"
      :class="{ 'db-content-time-series-graph--preview': isPreview }"
    >
      <CmkIcon
        v-if="isDiscovering"
        name="load-graph"
        size="xlarge"
        class="db-content-time-series-graph__loading-icon"
      />
      <div v-else-if="errorMessage" class="db-content-time-series-graph__error error">
        {{ errorMessage }}
      </div>
      <div v-else-if="noDataMessage" class="db-content-time-series-graph__no-data">
        <CmkHtml :html="noDataMessage" />
      </div>
      <GraphFigure
        v-else-if="shell"
        :internal="shell.internal"
        :y-axis="shell.y_axis"
        :timerange="timerange"
        :combination-mode="combinationMode"
        :show-legend="showLegend"
        :show-timestamp="showTimestamp"
        :show-pin="showPin"
        :show-time-axis="showTimeAxis"
        :show-value-axis="showValueAxis"
        :show-margin="showMargin"
        :min-value-axis-width="valueAxisWidth"
        :fetch-graph="fetchGraph"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-time-series-graph {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;

  &.db-content-time-series-graph--preview {
    pointer-events: none;
  }
}

.db-content-time-series-graph__loading-icon {
  margin: auto;
}

.db-content-time-series-graph__error {
  padding: var(--dimension-6);
}

.db-content-time-series-graph__no-data {
  padding: var(--dimension-6);
  color: var(--font-color-dimmed);
}
</style>
