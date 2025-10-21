/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  HostStateContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

export interface UseHostState extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  showBackgroundInStatusColorAndLabel: Ref<boolean>
  colorizeStates: Ref<string>
  showSummaryForNonUpStates: Ref<boolean>
}

export const useHostState = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseHostState> => {
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

  const currentContent = currentSpec?.content as HostStateContent

  const showBackgroundInStatusColorAndLabel = ref<boolean>(!!currentContent?.status_display)
  const colorizeStates = ref<string>(currentContent?.status_display?.for_states ?? 'all')
  const showSummaryForNonUpStates = ref<boolean>(currentContent?.show_summary === 'not_ok')

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): HostStateContent => {
    const content: HostStateContent = {
      type: 'host_state'
    }

    if (showSummaryForNonUpStates.value) {
      content.show_summary = 'not_ok'
    }

    if (showBackgroundInStatusColorAndLabel.value) {
      content.status_display = {
        type: 'background',
        for_states: colorizeStates.value === 'all' ? 'all' : 'not_ok'
      }
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
    [
      widgetGeneralSettings,
      showBackgroundInStatusColorAndLabel,
      colorizeStates,
      showSummaryForNonUpStates
    ],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    showBackgroundInStatusColorAndLabel,
    colorizeStates,
    showSummaryForNonUpStates,

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
