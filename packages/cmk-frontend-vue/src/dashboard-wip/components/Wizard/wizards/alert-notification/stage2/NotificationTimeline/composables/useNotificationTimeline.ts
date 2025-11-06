/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { type Suggestions } from '@/components/CmkSuggestions'

import { type GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard-wip/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  NotificationTimelineContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

import { VisualizationTimelineType } from '../../../composables/useSelectGraphTypes.ts'

const { _t } = usei18n()

export interface UseNotificationTimeline extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  timeRangeType: Ref<TimeRangeType>
  timeRange: Ref<GraphTimerange>
  timeResolution: Ref<'hour' | 'day'>
  visualizationType: Ref<VisualizationTimelineType>
  logtarget: Ref<'both' | 'host' | 'service'>
  logtargetOptions: Suggestions
  isUpdating: Ref<boolean>
}

type TimeRangeType = 'current' | 'window'

export const useNotificationTimeline = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseNotificationTimeline> => {
  const isUpdating = ref(false)
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

  const currentContent = currentSpec?.content as NotificationTimelineContent

  let initialTimeResolution: 'hour' | 'day' = 'hour'
  if (
    currentContent?.render_mode &&
    'time_resolution' in currentContent.render_mode &&
    typeof currentContent.render_mode.time_resolution === 'string'
  ) {
    if (
      currentContent.render_mode.time_resolution === 'hour' ||
      currentContent.render_mode.time_resolution === 'day'
    ) {
      initialTimeResolution = currentContent.render_mode.time_resolution
    }
  }
  const timeResolution = ref<'hour' | 'day'>(initialTimeResolution)
  const visualizationType = ref<VisualizationTimelineType>(VisualizationTimelineType.BARPLOT)

  const logtarget = ref<'both' | 'host' | 'service'>(currentContent?.log_target ?? 'both')
  const logtargetOptions: Suggestions = {
    type: 'fixed',
    suggestions: [
      {
        name: 'both',
        title: _t('Show notifications for hosts and services') as TranslatedString
      },
      {
        name: 'host',
        title: _t('Show notifications for hosts only') as TranslatedString
      },
      {
        name: 'service',
        title: _t('Show notifications for services only') as TranslatedString
      }
    ]
  }

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): NotificationTimelineContent => {
    if (visualizationType.value === VisualizationTimelineType.METRIC) {
      return {
        type: 'notification_timeline',
        log_target: logtarget.value,
        render_mode: {
          type: 'simple_number',
          time_range: generateTimeRangeProps()
        }
      }
    }
    return {
      type: 'notification_timeline',
      log_target: logtarget.value,
      render_mode: {
        type: 'bar_chart',
        time_range: generateTimeRangeProps(),
        time_resolution: timeResolution.value ?? 'day'
      }
    }
  }

  const _updateWidgetProps = async () => {
    isUpdating.value = true
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
    isUpdating.value = false
  }

  watch(
    [timeRangeType, timeRange, timeResolution, visualizationType, logtarget, widgetGeneralSettings],
    useDebounceFn(async () => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    timeRangeType,
    timeRange,
    timeResolution,
    visualizationType,
    logtarget,
    logtargetOptions,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>,
    isUpdating
  }
}
