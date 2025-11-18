/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { type GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard-wip/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  AlertTimelineContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

import { VisualizationTimelineType } from '../../../composables/useSelectGraphTypes.ts'

export interface UseAlertTimeline extends UseWidgetHandler, UseWidgetVisualizationOptions {
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>
  timeResolution: Ref<'hour' | 'day'>
  visualizationType: Ref<VisualizationTimelineType>
  isUpdating: Ref<boolean>
}

type TimeRangeType = 'current' | 'window'

export const useAlertTimeline = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseAlertTimeline> => {
  const isUpdating = ref(false)
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

  const timeResolution = ref<'hour' | 'day'>('hour')
  const visualizationType = ref<VisualizationTimelineType>(VisualizationTimelineType.BARPLOT)
  const widgetProps = ref<WidgetProps>()

  const currentContent = currentSpec?.content as AlertTimelineContent
  const { timeRange, widgetProps: generateTimeRangeProps } = useTimeRange(
    currentContent?.render_mode?.time_range ?? null
  )

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): AlertTimelineContent => {
    if (visualizationType.value === VisualizationTimelineType.METRIC) {
      return {
        type: 'alert_timeline',
        log_target: 'both',
        render_mode: {
          type: 'simple_number',
          time_range: generateTimeRangeProps()
        }
      }
    }
    return {
      type: 'alert_timeline',
      log_target: 'both',
      render_mode: {
        type: 'bar_chart',
        time_range: generateTimeRangeProps(),
        time_resolution: timeResolution.value ?? 'day'
      }
    }
  }

  const _updateWidgetProps = async () => {
    isUpdating.value = true
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
    isUpdating.value = false
  }

  watch(
    [timeRangeType, timeRange, timeResolution, visualizationType, widgetGeneralSettings],
    useDebounceFn(async () => {
      await _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    timeRangeType,
    timeRange,
    timeResolution,
    visualizationType,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>,
    isUpdating
  }
}
