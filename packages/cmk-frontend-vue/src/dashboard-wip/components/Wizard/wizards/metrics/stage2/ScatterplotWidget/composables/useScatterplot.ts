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
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  ScatterplotContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

import { type UseAdditionalOptions, useAdditionalOptions } from './useAdditionalOptions'

const { _t } = usei18n()

export interface UseScatterplot
  extends UseWidgetHandler,
    UseWidgetVisualizationOptions,
    UseAdditionalOptions {
  timeRange: Ref<GraphTimerange>
  widgetProps: Ref<WidgetProps>
}

export const useScatterplot = (metric: string, filters: ConfiguredFilters): UseScatterplot => {
  //Todo: Fill values if they exist in serializedData
  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(_t('Time range'))

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

  const { metricColor, averageColor, medianColor } = useAdditionalOptions()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: ScatterplotContent = {
      type: 'average_scatterplot',
      metric,
      time_range: generateTimeRangeSpec(),
      metric_color: metricColor.value,
      average_color: averageColor.value,
      median_color: medianColor.value
    }

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [
      timeRange,
      title,
      showTitle,
      showTitleBackground,
      showWidgetBackground,
      titleUrlEnabled,
      titleUrl,
      titleUrlValidationErrors,
      metricColor,
      averageColor,
      medianColor
    ],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

  return {
    timeRange,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    metricColor,
    averageColor,
    medianColor,

    titleUrlValidationErrors,
    validate,

    widgetProps
  }
}
