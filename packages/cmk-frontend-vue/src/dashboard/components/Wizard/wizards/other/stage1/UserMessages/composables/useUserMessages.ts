/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onBeforeMount, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  UseWidgetHandler,
  UserMessagesContent,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext, dashboardAPI } from '@/dashboard/utils'

const { _t } = usei18n()
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

  if (!title.value) {
    title.value = _t('User message')
  }

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
