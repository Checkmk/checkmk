/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onBeforeMount, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  UseWidgetHandler,
  UserMessagesContent,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { buildWidgetEffectiveFilterContext, dashboardAPI } from '@/dashboard-wip/utils'

export interface UseUserMessages extends UseWidgetHandler, UseWidgetVisualizationOptions {}

export function useUserMessages(
  dashboardConstants: DashboardConstants,
  currentSpec: WidgetSpec | null
): UseUserMessages {
  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate,
    widgetGeneralSettings
  } = useWidgetVisualizationProps('', currentSpec?.general_settings)

  const content: UserMessagesContent = {
    type: 'user_messages'
  }

  const usesInfos = ref<string[]>([])
  onBeforeMount(async () => {
    const resp = await dashboardAPI.computeWidgetAttributes(content)
    usesInfos.value = resp.value.filter_context.uses_infos
  })

  const widgetProps = ref<WidgetProps>(_buildWidgetProps())

  function _buildWidgetProps(): WidgetProps {
    return {
      general_settings: widgetGeneralSettings.value,
      content,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content,
        {},
        usesInfos.value,
        dashboardConstants
      )
    }
  }
  watch(
    [widgetGeneralSettings, usesInfos],
    useDebounceFn(() => {
      widgetProps.value = _buildWidgetProps()
    }, 300),
    { deep: true }
  )

  return {
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
