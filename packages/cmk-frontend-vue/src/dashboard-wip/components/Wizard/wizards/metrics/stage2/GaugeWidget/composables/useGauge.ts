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
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

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

export const useGauge = async (
  metric: string,
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseGauge> => {
  const currentContent = currentSpec?.content as GaugeContent

  const timeRangeType = ref<TimeRangeType>('current')
  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(_t('Time range'))

  const {
    symbol: dataRangeSymbol,
    maximum: dataRangeMax,
    minimum: dataRangeMin,
    fixedDataRangeProps
  } = useFixedDataRange(
    currentContent?.display_range?.unit,
    currentContent?.display_range?.maximum,
    currentContent?.display_range?.minimum
  )

  // TODO: This field is incomplete, both here and the vue component.
  // Its missing a dropdwon with 3 options - CMK-26777
  const showServiceStatus = ref<boolean>(false)

  const {
    title,
    showTitle,
    showTitleBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    widgetGeneralSettings,
    showWidgetBackground
  } = useWidgetVisualizationProps(metric, currentSpec?.general_settings)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): GaugeContent => {
    return {
      type: 'gauge',
      metric: metric,
      display_range: fixedDataRangeProps.value,
      time_range: {
        type: 'window',
        window: generateTimeRangeSpec(),
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
    [timeRangeType, timeRange, fixedDataRangeProps, showServiceStatus, showWidgetBackground],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

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

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
