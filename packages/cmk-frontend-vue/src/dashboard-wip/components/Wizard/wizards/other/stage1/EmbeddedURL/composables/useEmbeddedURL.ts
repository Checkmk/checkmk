/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  URLContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

const CONTENT_TYPE = 'url'
export interface UseEmbeddedURL extends UseWidgetHandler, UseWidgetVisualizationOptions {
  url: Ref<string>
}

export function useEmbeddedURL(
  dashboardConstants: DashboardConstants,
  currentSpec: WidgetSpec | null
): UseEmbeddedURL {
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

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE ? (currentSpec?.content as URLContent) : undefined

  const url = ref(currentContent?.url || '')

  const content = computed<URLContent>(() => {
    return {
      type: CONTENT_TYPE,
      url: url.value
    }
  })

  const widgetProps = ref<WidgetProps>(_buildWidgetProps())

  function _buildWidgetProps(): WidgetProps {
    return {
      general_settings: widgetGeneralSettings.value,
      content: content.value,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content.value,
        {},
        [], // we know this doesn't use any infos, no need to ask the backend
        dashboardConstants
      )
    }
  }
  watch(
    [widgetGeneralSettings, content],
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

    url,

    widgetProps
  }
}
