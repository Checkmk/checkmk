/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { useDataRangeInput } from '@/dashboard-wip/components/Wizard/components/DataRangeInput/useDataRangeInput'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  BarplotContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

type DataRangeType = 'fixed' | 'automatic'

export interface UseBarplot extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  dataRangeType: Ref<DataRangeType>
  dataRangeSymbol: Ref<string>
  dataRangeMin: Ref<number>
  dataRangeMax: Ref<number>
}

export const useBarplot = (metric: string, filters: ConfiguredFilters): UseBarplot => {
  //Todo: Fill values if they exist in serializedData
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

  const {
    type: dataRangeType,
    symbol,
    maximum,
    minimum,
    widgetProps: dataRangeProps
  } = useDataRangeInput()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: BarplotContent = {
      type: 'barplot',
      metric: metric,
      display_range: dataRangeProps()
    }

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [
      dataRangeType,
      title,
      showTitle,
      showTitleBackground,
      titleUrlEnabled,
      titleUrl,
      symbol,
      maximum,
      minimum
    ],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

  return {
    dataRangeType,
    dataRangeSymbol: symbol,
    dataRangeMin: minimum,
    dataRangeMax: maximum,

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
