/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import {
  type DataRangeType,
  useDataRangeInput
} from '@/dashboard-wip/components/Wizard/components/DataRangeInput/useDataRangeInput'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  TopListContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

const { _t } = usei18n()

const MAX_ENTRIES = 50

export interface UseTopList extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  dataRangeType: Ref<DataRangeType>
  dataRangeSymbol: Ref<string>
  dataRangeMin: Ref<number>
  dataRangeMax: Ref<number>

  rankingOrder: Ref<'high' | 'low'>
  limitTo: Ref<number>
  showServiceName: Ref<boolean>
  showBarVisualizaton: Ref<boolean>

  MAX_ENTRIES: number
  limitToValidationErrors: Ref<string[]>

  widgetProps: Ref<WidgetProps>
}

export const useTopList = async (
  metric: string,
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseTopList> => {
  const currentContent = currentSpec?.content as TopListContent

  //Todo: Fill values if they exist in serializedData
  const {
    type: dataRangeType,
    symbol: dataRangeSymbol,
    maximum: dataRangeMax,
    minimum: dataRangeMin,
    dataRangeProps
  } = useDataRangeInput(currentContent?.display_range)

  const rankingOrder = ref<'high' | 'low'>(currentContent?.ranking_order ?? 'high')

  const limitTo = ref<number>(currentContent?.limit_to ?? 10)
  const showServiceName = ref<boolean>(currentContent?.columns?.show_service_description ?? true)
  const showBarVisualizaton = ref<boolean>(currentContent?.columns?.show_bar_visualization ?? true)

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    validate: validateTitle,
    titleUrlValidationErrors,
    widgetGeneralSettings
  } = useWidgetVisualizationProps(metric, currentSpec?.general_settings)

  const limitToValidationErrors = ref<string[]>([])

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    limitToValidationErrors.value = []

    if (limitTo.value > MAX_ENTRIES) {
      limitToValidationErrors.value.push(_t('Value out of range'))
    }

    validateTitle()

    return titleUrlValidationErrors.value.length + limitToValidationErrors.value.length === 0
  }

  const _generateContent = (): TopListContent => {
    return {
      type: 'top_list',
      metric: metric,
      columns: {
        show_bar_visualization: showBarVisualizaton.value,
        show_service_description: showServiceName.value
      },
      display_range: dataRangeProps.value,
      ranking_order: rankingOrder.value,
      limit_to: limitTo.value
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
    [dataRangeProps, widgetGeneralSettings, limitTo, rankingOrder],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    dataRangeType,
    dataRangeSymbol,
    dataRangeMin,
    dataRangeMax,

    rankingOrder,
    limitTo,
    showServiceName,
    showBarVisualizaton,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    MAX_ENTRIES,
    titleUrlValidationErrors,
    limitToValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
