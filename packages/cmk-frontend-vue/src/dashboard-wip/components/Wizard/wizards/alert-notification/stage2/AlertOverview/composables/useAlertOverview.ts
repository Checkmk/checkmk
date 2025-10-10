/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import { type GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard-wip/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  AlertOverviewContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

const { _t } = usei18n()

export interface UseAlertOverview extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>

  objectsEnabled: Ref<boolean>
  objectsLimit: Ref<number>

  widgetProps: Ref<WidgetProps>
}

type TimeRangeType = 'current' | 'window'

export const useAlertOverview = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseAlertOverview> => {
  const timeRangeType = ref<TimeRangeType>('current')
  const { timeRange, widgetProps: generateTimeRangeProps } = useTimeRange(_t('Time range'))

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
  } = useWidgetVisualizationProps('', currentSpec?.general_settings)

  const currentContent = currentSpec?.content as AlertOverviewContent

  const objectsLimit = ref<number>(currentContent?.limit_objects ?? 0)
  const objectsEnabled = ref<boolean>(objectsLimit.value !== undefined)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): AlertOverviewContent => {
    const content: AlertOverviewContent = {
      type: 'alert_overview',
      time_range: generateTimeRangeProps(),
      ...(objectsLimit.value !== undefined ? { limit_objects: objectsLimit.value } : {})
    }

    return content
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
    [timeRangeType, timeRange, widgetGeneralSettings],
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
