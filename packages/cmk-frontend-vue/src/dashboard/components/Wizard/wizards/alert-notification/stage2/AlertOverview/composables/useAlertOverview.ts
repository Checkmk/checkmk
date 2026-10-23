/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, ref, watch } from 'vue'

import { type GraphTimerange } from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import { useTimeRangeSource } from '@/dashboard/components/TimeRange/useTimeRangeSource'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  AlertOverviewContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

export interface UseAlertOverview extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  followDashboardTimeRange: Ref<boolean>
  timeRange: Ref<GraphTimerange>

  objectsEnabled: Ref<boolean>
  objectsLimit: Ref<number>
}

const CONTENT_TYPE = 'alert_overview'

export const useAlertOverview = async (
  filters: ConfiguredFilters,
  currentSpec: WidgetSpec | null
): Promise<UseAlertOverview> => {
  const constants = useInjectDashboardConstants()
  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    widgetGeneralSettings,
    titleMacros
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings, CONTENT_TYPE)

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as AlertOverviewContent)
      : null
  const {
    followDashboard: followDashboardTimeRange,
    timeRange,
    widgetProps: generateTimeRangeProps
  } = useTimeRangeSource(currentContent?.time_range ?? null)

  const objectsEnabled = ref<boolean>(!!currentContent?.limit_objects)
  const objectsLimit = ref<number>(currentContent?.limit_objects ?? 100)

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): AlertOverviewContent => {
    return {
      type: CONTENT_TYPE,
      time_range: generateTimeRangeProps(),
      ...(objectsEnabled.value ? { limit_objects: objectsLimit.value } : {})
    }
  }

  const _computeWidgetProps = async (): Promise<WidgetProps> => {
    const content = _generateContent()
    const [effectiveTitle, effectiveFilterContext] = await Promise.all([
      computePreviewWidgetTitle({
        generalSettings: widgetGeneralSettings.value,
        content,
        effectiveFilters: filters
      }),
      determineWidgetEffectiveFilterContext(content, filters, constants)
    ])

    return {
      general_settings: widgetGeneralSettings.value,
      content,
      effectiveTitle,
      effective_filter_context: effectiveFilterContext
    }
  }

  const _updateWidgetProps = async () => {
    widgetProps.value = await _computeWidgetProps()
  }

  watch(
    [followDashboardTimeRange, timeRange, widgetGeneralSettings, objectsEnabled, objectsLimit],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    followDashboardTimeRange,
    timeRange,
    objectsEnabled,
    objectsLimit,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleMacros,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>,
    getSubmitProps: _computeWidgetProps
  }
}
