/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import type { GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard-wip/components/TimeRange/useTimeRange'
import {
  type UseGraphRenderOptions,
  useGraphRenderOptions
} from '@/dashboard-wip/components/Wizard/components/GraphRenderOptions/useGraphRenderOptions'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  CustomGraphContent,
  UseValidate,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

const { _t } = usei18n()

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
  const currentContent = currentSpec?.content as CustomGraphContent

  const customGraph = ref<string | null>(currentContent?.custom_graph || null)
  const customGraphValidationErrors = ref<string[]>([])

  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(_t('Time range'))

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
  } = useWidgetVisualizationProps(customGraph.value || '', currentSpec?.general_settings)

  const {
    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    fontSize,
    color,
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
      type: 'custom_graph',
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

    widgetProps.value = {
      general_settings: widgetGeneralSettings.value,
      content,
      effective_filter_context: await determineWidgetEffectiveFilterContext(
        content,
        filters,
        dashboardConstants
      )
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
    color,
    timestamp,
    roundMargin,
    graphLegend,
    clickToPlacePin,
    showBurgerMenu,
    dontFollowTimerange,

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
