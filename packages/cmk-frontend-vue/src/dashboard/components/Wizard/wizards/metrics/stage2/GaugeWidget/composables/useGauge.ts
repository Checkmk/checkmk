/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import type { TimerangeModel } from '@/dashboard/components/TimeRange/types'
import { useTimeRange } from '@/dashboard/components/TimeRange/useTimeRange'
import { useFixedDataRange } from '@/dashboard/components/Wizard/components/FixedDataRangeInput/useFixedDataRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  ForStates,
  GaugeContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

type TimeRangeType = 'current' | 'window'

const CONTENT_TYPE = 'gauge'

export type ShowServiceStatusType = 'disabled' | 'text' | 'background'
export interface UseGauge extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Time range
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>

  //Data settings
  dataRangeSymbol: Ref<string>
  dataRangeMax: Ref<number>
  dataRangeMin: Ref<number>
  showServiceStatus: Ref<ShowServiceStatusType>
  showServiceStatusSelection: Ref<ForStates | null>
}

export const useGauge = async (
  metric: string,
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseGauge> => {
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE ? (currentSpec?.content as GaugeContent) : null

  const timeRangeType = ref<TimeRangeType>('current')
  const currentTimerange: TimerangeModel | null =
    currentContent?.time_range === 'current' ? null : currentContent?.time_range?.window || null
  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(currentTimerange)

  const {
    symbol: dataRangeSymbol,
    maximum: dataRangeMax,
    minimum: dataRangeMin,
    fixedDataRangeProps
  } = useFixedDataRange(
    currentContent?.display_range?.unit,
    currentContent?.display_range?.minimum,
    currentContent?.display_range?.maximum
  )

  const showServiceStatus = ref<ShowServiceStatusType>(
    currentContent?.status_display?.type ?? 'disabled'
  )
  const showServiceStatusSelection = ref<ForStates | null>(
    currentContent?.status_display?.for_states ?? null
  )

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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): GaugeContent => {
    const content: GaugeContent = {
      type: CONTENT_TYPE,
      metric: metric,
      display_range: fixedDataRangeProps.value,
      time_range: {
        type: 'window',
        window: generateTimeRangeSpec(),
        consolidation: 'average'
      }
    }

    if (showServiceStatus.value !== 'disabled' && showServiceStatusSelection.value) {
      content.status_display = {
        type: showServiceStatus.value,
        for_states: showServiceStatusSelection.value
      }
    }

    return content
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
    [
      timeRangeType,
      timeRange,
      fixedDataRangeProps,
      showServiceStatus,
      showServiceStatusSelection,
      showWidgetBackground,
      widgetGeneralSettings
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

    dataRangeSymbol,
    dataRangeMax,
    dataRangeMin,
    showServiceStatus,
    showServiceStatusSelection,

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
