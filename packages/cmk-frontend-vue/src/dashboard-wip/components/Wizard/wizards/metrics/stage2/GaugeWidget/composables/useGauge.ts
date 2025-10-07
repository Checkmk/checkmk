/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import type { GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard-wip/components/TimeRange/useTimeRange'
import { useFixedDataRange } from '@/dashboard-wip/components/Wizard/components/FixedDataRangeInput/useFixedDataRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  GaugeContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

const { _t } = usei18n()

type TimeRangeType = 'current' | 'window'

export interface UseGauge extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Time range
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>

  //Data settings
  dataRangeSymbol: Ref<string>
  dataRangeMax: Ref<number>
  dataRangeMin: Ref<number>
  showServiceStatus: Ref<boolean>
}

export const useGauge = (metric: string, filters: ConfiguredFilters): UseGauge => {
  //Todo: Fill values if they exist in serializedData

  const timeRangeType = ref<TimeRangeType>('current')
  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(_t('Time range'))

  const {
    symbol: dataRangeSymbol,
    maximum: dataRangeMax,
    minimum: dataRangeMin,
    widgetProps: dataRangeProps
  } = useFixedDataRange()

  const showServiceStatus = ref<boolean>(false)

  const {
    title,
    showTitle,
    showTitleBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    generateTitleSpec,
    showWidgetBackground
  } = useWidgetVisualizationProps(metric)

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: GaugeContent = {
      type: 'gauge',
      metric: metric,
      display_range: dataRangeProps(),
      time_range: {
        type: 'window',
        window: generateTimeRangeSpec(),
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
      dataRangeSymbol,
      dataRangeMax,
      dataRangeMin,
      showServiceStatus,
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

    dataRangeSymbol,
    dataRangeMax,
    dataRangeMin,
    showServiceStatus,

    title,
    showTitle,
    showTitleBackground,
    titleUrlEnabled,
    titleUrl,
    showWidgetBackground,

    titleUrlValidationErrors,
    validate,

    widgetProps
  }
}
