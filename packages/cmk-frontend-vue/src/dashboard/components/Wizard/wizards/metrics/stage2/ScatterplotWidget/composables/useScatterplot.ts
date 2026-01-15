/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  ScatterplotContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

import { type UseAdditionalOptions, useAdditionalOptions } from './useAdditionalOptions'

const CONTENT_TYPE = 'average_scatterplot'
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
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as ScatterplotContent)
      : null

  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(
    currentContent?.time_range ?? null
  )

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
      type: CONTENT_TYPE,
      metric,
      time_range: generateTimeRangeSpec(),
      metric_color: metricColor.value === 'default' ? 'default' : metricColor.value.toUpperCase(),
      average_color:
        averageColor.value === 'default' ? 'default' : averageColor.value.toUpperCase(),
      median_color: medianColor.value === 'default' ? 'default' : medianColor.value.toUpperCase()
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
