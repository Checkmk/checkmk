/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, ref, watch } from 'vue'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRangeSource } from '@/dashboard/components/TimeRange/useTimeRangeSource'
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
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

const { _t } = usei18n()

const CONTENT_TYPE = 'custom_graph'
export interface UseCustomGraph
  extends UseValidate, UseGraphRenderOptions, UseWidgetVisualizationOptions {
  customGraph: Ref<string | null>
  customGraphValidationErrors: Ref<string[]>
  followDashboardTimeRange: Ref<boolean>
  timeRange: Ref<GraphTimerange>

  widgetProps: Ref<WidgetProps | null>
  getSubmitProps: () => Promise<WidgetProps>
}

export const useCustomGraph = async (
  filters: ConfiguredFilters,
  currentSpec?: WidgetSpec | null
): Promise<UseCustomGraph> => {
  const constants = useInjectDashboardConstants()
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as CustomGraphContent)
      : null

  const customGraph = ref<string | null>(currentContent?.custom_graph || null)
  const customGraphValidationErrors = ref<string[]>([])

  const {
    followDashboard: followDashboardTimeRange,
    timeRange,
    widgetProps: generateTimeRangeSpec
  } = useTimeRangeSource(currentContent?.timerange ?? null)

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    widgetGeneralSettings,
    titleMacros
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings, CONTENT_TYPE)

  const {
    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    timestamp,
    roundMargin,
    graphLegend,
    graphLegendStyle,
    clickToPlacePin,
    showBurgerMenu,
    graphRenderOptions
  } = useGraphRenderOptions(currentContent?.graph_render_options, currentContent === null)

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

  const _computeWidgetProps = async (): Promise<WidgetProps> => {
    const content = _generateContent()
    const [effectiveTitle, effectiveFilterContext] = await Promise.all([
      computePreviewWidgetTitle({
        generalSettings: widgetGeneralSettings.value,
        content,
        effectiveFilters: filters
      }),
      determineWidgetEffectiveFilterContext(content, filters, constants)
    ])

    return {
      general_settings: widgetGeneralSettings.value,
      content,
      effectiveTitle,
      effective_filter_context: effectiveFilterContext
    }
  }

  const _updateWidgetProps = async () => {
    if (!customGraph.value) {
      widgetProps.value = null
      return
    }
    widgetProps.value = await _computeWidgetProps()
  }

  watch([customGraph], (selectedGraph) => {
    if (selectedGraph) {
      customGraphValidationErrors.value = []
    }
  })

  watch(
    [customGraph, followDashboardTimeRange, timeRange, widgetGeneralSettings, graphRenderOptions],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    customGraph,
    customGraphValidationErrors,
    followDashboardTimeRange,
    timeRange,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleMacros,

    titleUrlValidationErrors,
    validate,

    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    timestamp,
    roundMargin,
    graphLegend,
    graphLegendStyle,
    clickToPlacePin,
    showBurgerMenu,

    widgetProps: widgetProps as Ref<WidgetProps>,
    getSubmitProps: _computeWidgetProps
  }
}
