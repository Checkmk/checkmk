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
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

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

export const useTopList = (metric: string, filters: ConfiguredFilters): UseTopList => {
  //Todo: Fill values if they exist in serializedData
  const {
    type: dataRangeType,
    symbol: dataRangeSymbol,
    maximum: dataRangeMax,
    minimum: dataRangeMin,
    widgetProps: generateTimeRangeSpec
  } = useDataRangeInput()

  const rankingOrder = ref<'high' | 'low'>('high')

  const limitTo = ref<number>(10)
  const showServiceName = ref<boolean>(true)
  const showBarVisualizaton = ref<boolean>(true)

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    validate: validateTitle,
    titleUrlValidationErrors,
    generateTitleSpec
  } = useWidgetVisualizationProps(metric)

  const limitToValidationErrors = ref<string[]>([])

  const validate = (): boolean => {
    limitToValidationErrors.value = []

    if (limitTo.value > MAX_ENTRIES) {
      limitToValidationErrors.value.push(_t('Value out of range'))
    }

    validateTitle()

    return titleUrlValidationErrors.value.length + limitToValidationErrors.value.length === 0
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: TopListContent = {
      type: 'top_list',
      metric: metric,
      columns: {
        show_bar_visualization: showBarVisualizaton.value,
        show_service_description: showServiceName.value
      },
      display_range: generateTimeRangeSpec(),
      ranking_order: rankingOrder.value,
      limit_to: limitTo.value
    }

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [
      dataRangeType,
      dataRangeSymbol,
      dataRangeMin,
      dataRangeMax,

      showTitle,
      showTitleBackground,
      showWidgetBackground,
      titleUrlEnabled,
      titleUrl,
      limitTo,
      rankingOrder
    ],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )
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

    widgetProps
  }
}
