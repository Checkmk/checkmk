/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import type { TimerangeModel } from '@/dashboard/components/TimeRange/types'
import { useTimeRange } from '@/dashboard/components/TimeRange/useTimeRange'
import {
  type DataRangeType,
  useDataRangeInput
} from '@/dashboard/components/Wizard/components/DataRangeInput/useDataRangeInput'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  SingleMetricContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

const CONTENT_TYPE = 'single_metric'
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
  const currentContent = currentSpec?.content?.type === CONTENT_TYPE ? currentSpec?.content : null

  const timeRangeType = ref<TimeRangeType>(
    currentContent?.time_range === 'current' ? 'current' : 'window'
  )
  const currentTimerange: TimerangeModel | null =
    currentContent?.time_range === 'current' ? null : currentContent?.time_range?.window || null
  const { timeRange, widgetProps: generateTimeRangeProps } = useTimeRange(currentTimerange)
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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): SingleMetricContent => {
    return {
      type: CONTENT_TYPE,
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
