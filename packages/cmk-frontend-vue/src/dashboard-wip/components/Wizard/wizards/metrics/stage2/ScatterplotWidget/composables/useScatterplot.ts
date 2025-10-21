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
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

import { type UseAdditionalOptions, useAdditionalOptions } from './useAdditionalOptions'

const { _t } = usei18n()

export interface UseScatterplot
  extends UseWidgetHandler,
    UseWidgetVisualizationOptions,
    UseAdditionalOptions {
  timeRange: Ref<GraphTimerange>
  widgetProps: Ref<WidgetProps>
}

export const useScatterplot = async (
  metric: string,
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseScatterplot> => {
  const currentContent = currentSpec?.content as ScatterplotContent

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
    widgetGeneralSettings
  } = useWidgetVisualizationProps(metric, currentSpec?.general_settings)

  const { metricColor, averageColor, medianColor } = useAdditionalOptions(
    currentContent?.metric_color,
    currentContent?.average_color,
    currentContent?.median_color
  )

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): ScatterplotContent => {
    return {
      type: 'average_scatterplot',
      metric,
      time_range: generateTimeRangeSpec(),
      metric_color: metricColor.value,
      average_color: averageColor.value,
      median_color: medianColor.value
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
    [timeRange, widgetGeneralSettings, metricColor, averageColor, medianColor],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

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

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
