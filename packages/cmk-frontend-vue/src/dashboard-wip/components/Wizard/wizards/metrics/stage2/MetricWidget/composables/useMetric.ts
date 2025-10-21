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
  type DataRangeType,
  useDataRangeInput
} from '@/dashboard-wip/components/Wizard/components/DataRangeInput/useDataRangeInput'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  SingleMetricContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

const { _t } = usei18n()

export interface UseMetric extends UseWidgetHandler, UseWidgetVisualizationOptions {
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>
  displayRangeLimits: Ref<boolean>
  showServiceStatus: Ref<boolean>

  dataRangeType: Ref<DataRangeType>
  dataRangeSymbol: Ref<string>
  dataRangeMin: Ref<number>
  dataRangeMax: Ref<number>

  widgetProps: Ref<WidgetProps>
}

type TimeRangeType = 'current' | 'window'

export const useMetric = async (
  metric: string,
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseMetric> => {
  const currentContent = currentSpec?.content as SingleMetricContent

  const timeRangeType = ref<TimeRangeType>(
    currentContent?.time_range === 'current' ? 'current' : 'window'
  )
  const { timeRange, widgetProps: generateTimeRangeProps } = useTimeRange(_t('Time range'))
  const displayRangeLimits = ref<boolean>(currentContent?.show_display_range_limits ?? true)
  const showServiceStatus = ref<boolean>(true)

  const {
    type: dataRangeType,
    symbol: dataRangeSymbol,
    maximum: dataRangeMin,
    minimum: dataRangeMax,
    dataRangeProps
  } = useDataRangeInput(currentContent?.display_range)

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
  } = useWidgetVisualizationProps(metric, currentSpec?.general_settings)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): SingleMetricContent => {
    return {
      type: 'single_metric',
      metric: metric,
      display_range: dataRangeProps.value,
      show_display_range_limits: displayRangeLimits.value,
      time_range:
        timeRangeType.value === 'current'
          ? 'current'
          : {
              type: 'window',
              window: generateTimeRangeProps(),
              consolidation: 'average'
            }
    }
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
    [timeRangeType, timeRange, dataRangeType, dataRangeProps, widgetGeneralSettings],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    timeRangeType,
    timeRange,
    dataRangeType,
    dataRangeSymbol,
    dataRangeMin,
    dataRangeMax,
    displayRangeLimits,
    showServiceStatus,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
