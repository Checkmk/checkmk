/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { type GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  AlertOverviewContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

export interface UseAlertOverview extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>

  objectsEnabled: Ref<boolean>
  objectsLimit: Ref<number>
}

type TimeRangeType = 'current' | 'window'

const CONTENT_TYPE = 'alert_overview'

export const useAlertOverview = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseAlertOverview> => {
  const timeRangeType = ref<TimeRangeType>('current')
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

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as AlertOverviewContent)
      : null
  const { timeRange, widgetProps: generateTimeRangeProps } = useTimeRange(
    currentContent?.time_range ?? null
  )

  const objectsLimit = ref<number>(currentContent?.limit_objects ?? 0)
  const objectsEnabled = ref<boolean>(objectsLimit.value !== undefined)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): AlertOverviewContent => {
    return {
      type: CONTENT_TYPE,
      time_range: generateTimeRangeProps(),
      ...(objectsLimit.value !== undefined ? { limit_objects: objectsLimit.value } : {})
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
    [timeRangeType, timeRange, widgetGeneralSettings, objectsEnabled, objectsLimit],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    timeRangeType,
    timeRange,
    objectsEnabled,
    objectsLimit,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
