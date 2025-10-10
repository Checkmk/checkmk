/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import { type GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
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
  ProblemGraphContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

const { _t } = usei18n()

type TimeRangeType = 'current' | 'window'

export interface UsePercentageOfServiceProblems
  extends UseWidgetHandler,
    UseWidgetVisualizationOptions,
    UseGraphRenderOptions {
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>

  widgetProps: Ref<WidgetProps>
}

export const usePercentageOfServiceProblems = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UsePercentageOfServiceProblems> => {
  const timeRangeType = ref<TimeRangeType>('current')
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
  } = useWidgetVisualizationProps('', currentSpec?.general_settings)

  const currentContent = currentSpec?.content as ProblemGraphContent
  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(_t('Time range'))
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

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): ProblemGraphContent => {
    const content: ProblemGraphContent = {
      type: 'problem_graph',
      timerange: generateTimeRangeSpec(),
      graph_render_options: graphRenderOptions.value
    }
    return content
  }

  const _updateWidgetProps = async () => {
    const content = _generateContent()
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

  watch(
    [
      timeRangeType,
      timeRange,
      widgetGeneralSettings,
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
      dontFollowTimerange
    ],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    timeRangeType,
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
