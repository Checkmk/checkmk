/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRangeSource } from '@/dashboard/components/TimeRange/useTimeRangeSource'
import {
  type UseGraphRenderProps,
  useGraphRenderOptions
} from '@/dashboard/components/Wizard/components/GraphRenderOptions/useGraphRenderOptions'
import {
  type UseWidgetVisualizationProps,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { WidgetProps } from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { EmbeddedCustomGraphContent, WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'
import { computeEpochTimeRange } from '@/graphing/components/GraphFigure/computeEpochTimeRange'
import type { CustomGraphOptions } from '@/graphing/designer/api'
import {
  type DataFieldErrors,
  type UseCustomGraphOptions,
  useCustomGraphOptions
} from '@/graphing/designer/composables/useCustomGraphOptions'
import type { ApiDataSourceInput } from '@/graphing/designer/types'
import type { RequestedTimeRange } from '@/graphing/types'

import type { EmbeddedGraphDefinition } from '../../editor/types'

const CONTENT_TYPE = 'embedded_custom_graph'

const DEFAULT_GRAPH_OPTIONS: CustomGraphOptions = {
  unit: { type: 'first_entry_with_unit' },
  explicit_vertical_range: { type: 'auto' },
  omit_zero_metrics: false
}

export interface UseEmbeddedCustomGraph {
  visualization: UseWidgetVisualizationProps
  renderOptions: UseGraphRenderProps
  followDashboardTimeRange: Ref<boolean>
  timeRange: Ref<GraphTimerange>
  /** The widget's own window for the editor's preview; undefined follows the dashboard's. */
  previewTimeRange: ComputedRef<RequestedTimeRange | undefined>
  /** The graph's sources: a stored widget's until the data selection picks others. */
  dataSources: Ref<readonly ApiDataSourceInput[]>
  /** The graph options the editor previews; follows `graphOptionsForm` while it is valid. */
  graphOptions: Ref<CustomGraphOptions>
  graphOptionsForm: UseCustomGraphOptions
  graphOptionErrors: Ref<DataFieldErrors>
  /** Whether the widget settings around the graph definition can be saved. */
  validate: () => boolean
  content: () => EmbeddedCustomGraphContent
  /** The widget as the preview renders and the dashboard stores it, under the given filters. */
  computeWidgetProps: (filters: ConfiguredFilters) => Promise<WidgetProps>
}

export function useEmbeddedCustomGraph(currentSpec?: WidgetSpec | null): UseEmbeddedCustomGraph {
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec.content as EmbeddedCustomGraphContent)
      : null
  const definition = currentContent?.definition as Partial<EmbeddedGraphDefinition> | undefined
  const constants = useInjectDashboardConstants()

  const visualization = useWidgetVisualizationProps(
    '$DEFAULT_TITLE$',
    currentSpec?.general_settings,
    CONTENT_TYPE
  )
  const renderOptions = useGraphRenderOptions(
    currentContent?.graph_render_options,
    currentContent === null
  )
  const {
    followDashboard: followDashboardTimeRange,
    timeRange,
    widgetProps: timeRangeSpec
  } = useTimeRangeSource(currentContent?.timerange ?? null)
  const previewTimeRange = computed(() => {
    const spec = timeRangeSpec()
    return spec === 'dashboard' ? undefined : computeEpochTimeRange(spec)
  })

  const graphOptions = ref<CustomGraphOptions>(definition?.graph_options ?? DEFAULT_GRAPH_OPTIONS)
  const graphOptionsForm = useCustomGraphOptions(() => graphOptions.value)
  const graphOptionErrors = ref<DataFieldErrors>({})
  watch(
    () => graphOptionsForm.validate(),
    (result) => {
      if (!result.isValid) {
        graphOptionErrors.value = result.errors
        return
      }
      graphOptionErrors.value = {}
      if (JSON.stringify(result.graphOptions) !== JSON.stringify(graphOptions.value)) {
        graphOptions.value = result.graphOptions
      }
    }
  )

  const dataSources = ref<readonly ApiDataSourceInput[]>(definition?.data_sources ?? [])

  const content = (): EmbeddedCustomGraphContent => ({
    type: CONTENT_TYPE,
    definition: { data_sources: dataSources.value, graph_options: graphOptions.value },
    timerange: timeRangeSpec(),
    graph_render_options: renderOptions.graphRenderOptions.value
  })

  const computeWidgetProps = async (filters: ConfiguredFilters): Promise<WidgetProps> => {
    const widgetContent = content()
    const generalSettings = visualization.widgetGeneralSettings.value
    const [effectiveTitle, effectiveFilterContext] = await Promise.all([
      computePreviewWidgetTitle({
        generalSettings,
        content: widgetContent,
        effectiveFilters: filters
      }),
      determineWidgetEffectiveFilterContext(widgetContent, filters, constants)
    ])
    return {
      general_settings: generalSettings,
      content: widgetContent,
      effectiveTitle,
      effective_filter_context: effectiveFilterContext
    }
  }

  return {
    visualization,
    renderOptions,
    followDashboardTimeRange,
    timeRange,
    previewTimeRange,
    dataSources,
    graphOptions,
    graphOptionsForm,
    graphOptionErrors,
    validate: () => {
      const isTitleValid = visualization.validate()
      return isTitleValid && Object.keys(graphOptionErrors.value).length === 0
    },
    content,
    computeWidgetProps
  }
}
