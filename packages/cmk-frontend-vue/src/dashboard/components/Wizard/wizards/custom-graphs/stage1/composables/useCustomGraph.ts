/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard/components/TimeRange/useTimeRange'
import {
  type UseGraphRenderOptions,
  useGraphRenderOptions
} from '@/dashboard/components/Wizard/components/GraphRenderOptions/useGraphRenderOptions'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  CustomGraphContent,
  UseValidate,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

const { _t } = usei18n()

const CONTENT_TYPE = 'custom_graph'
export interface UseCustomGraph
  extends UseValidate,
    UseGraphRenderOptions,
    UseWidgetVisualizationOptions {
  customGraph: Ref<string | null>
  customGraphValidationErrors: Ref<string[]>
  timeRange: Ref<GraphTimerange>

  widgetProps: Ref<WidgetProps | null>
}

export const useCustomGraph = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseCustomGraph> => {
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as CustomGraphContent)
      : null

  const customGraph = ref<string | null>(currentContent?.custom_graph || null)
  const customGraphValidationErrors = ref<string[]>([])

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

  const widgetProps = ref<WidgetProps | null>(null)

  const _validateGraph = (): boolean => {
    customGraphValidationErrors.value = []
    let isGraphValid = true
    if (!customGraph.value || customGraph.value.trim() === '') {
      customGraphValidationErrors.value.push(_t('Must select a custom graph'))
      isGraphValid = false
    }
    return isGraphValid
  }

  const validate = (): boolean => {
    const isTitleValid = validateTitle()
    const isGraphValid = _validateGraph()
    return isGraphValid && isTitleValid
  }

  const _generateContent = (): CustomGraphContent => {
    return {
      type: CONTENT_TYPE,
      timerange: generateTimeRangeSpec(),
      graph_render_options: graphRenderOptions.value,
      custom_graph: customGraph.value || ''
    }
  }

  const _updateWidgetProps = async () => {
    const content = _generateContent()

    if (!customGraph.value) {
      widgetProps.value = null
      return
    }

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

  watch([customGraph], (selectedGraph) => {
    if (selectedGraph) {
      customGraphValidationErrors.value = []
    }
  })

  watch(
    [customGraph, timeRange, widgetGeneralSettings, graphRenderOptions],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    customGraph,
    customGraphValidationErrors,
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

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
