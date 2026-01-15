/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  CombinedGraphContent,
  CombinedGraphContentPresentation,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

import {
  type UseGraphRenderOptions,
  useGraphRenderOptions
} from '../../../../../components/GraphRenderOptions/useGraphRenderOptions.ts'

const CONTENT_TYPE = 'combined_graph'
export interface UseCombinedGraph
  extends UseWidgetHandler,
    UseGraphRenderOptions,
    UseWidgetVisualizationOptions {
  timeRange: Ref<GraphTimerange>
  presentation: Ref<CombinedGraphContentPresentation>

  widgetProps: Ref<WidgetProps>
}

export const useCombinedGraph = async (
  metric: string,
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseCombinedGraph> => {
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as CombinedGraphContent)
      : null

  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(
    currentContent?.timerange ?? null
  )

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    widgetGeneralSettings
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings)

  const {
    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    fontSize,
    timestamp,
    roundMargin,
    graphLegend,
    clickToPlacePin,
    showBurgerMenu,
    dontFollowTimerange,
    graphRenderOptions
  } = useGraphRenderOptions(currentContent?.graph_render_options)

  const presentation = ref<CombinedGraphContentPresentation>(
    currentContent?.presentation ?? 'lines'
  )

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): CombinedGraphContent => {
    return {
      type: CONTENT_TYPE,
      timerange: generateTimeRangeSpec(),
      graph_render_options: graphRenderOptions.value,

      graph_template: currentContent?.graph_template ?? metric,
      presentation: 'lines'
    }
  }

  const _updateWidgetProps = async () => {
    const content = _generateContent()
    const [effectiveTitle, effectiveFilterContext] = await Promise.all([
      computePreviewWidgetTitle({
        generalSettings: widgetGeneralSettings.value,
        content,
        effectiveFilters: filters
      }),
      determineWidgetEffectiveFilterContext(content, filters, dashboardConstants)
    ])

    widgetProps.value = {
      general_settings: widgetGeneralSettings.value,
      content,
      effectiveTitle,
      effective_filter_context: effectiveFilterContext
    }
  }

  watch(
    [timeRange, widgetGeneralSettings, graphRenderOptions, presentation],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    timeRange,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    fontSize,
    timestamp,
    roundMargin,
    graphLegend,
    clickToPlacePin,
    showBurgerMenu,
    dontFollowTimerange,

    presentation,

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
