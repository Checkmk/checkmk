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
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

const { _t } = usei18n()

export interface UseMetric extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
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

export const useMetric = (metric: string, filters: ConfiguredFilters): UseMetric => {
  //Todo: Fill values if they exist in serializedData
  const timeRangeType = ref<TimeRangeType>('current')
  const { timeRange, widgetProps: generateTimeRangeProps } = useTimeRange(_t('Time range'))
  const displayRangeLimits = ref<boolean>(true)
  const showServiceStatus = ref<boolean>(true)

  const {
    type: dataRangeType,
    symbol: dataRangeSymbol,
    maximum: dataRangeMin,
    minimum: dataRangeMax,

    widgetProps: generateDataRangeProps
  } = useDataRangeInput()

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    generateTitleSpec
  } = useWidgetVisualizationProps(metric)

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: SingleMetricContent = {
      type: 'single_metric',
      metric: metric,
      display_range: generateDataRangeProps(),
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
    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [
      timeRangeType,
      timeRange,
      dataRangeType,
      dataRangeSymbol,
      dataRangeMin,
      dataRangeMax,
      dataRangeType,
      title,
      showTitle,
      showTitleBackground,
      titleUrlEnabled,
      titleUrl
    ],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

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

    widgetProps
  }
}
