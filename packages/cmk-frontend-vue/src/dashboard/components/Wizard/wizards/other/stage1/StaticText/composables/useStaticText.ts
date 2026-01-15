/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { UseWidgetHandler, WidgetProps } from '@/dashboard/components/Wizard/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { StaticTextContent, WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard/utils'

const CONTENT_TYPE = 'static_text'

export interface UseStaticText extends UseWidgetHandler, UseWidgetVisualizationOptions {
  text: Ref<string>
}

export function useStaticText(
  dashboardConstants: DashboardConstants,
  currentSpec: WidgetSpec | null
): UseStaticText {
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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings)

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as StaticTextContent)
      : undefined
  const text = ref(currentContent?.text || '')

  const content = computed<StaticTextContent>(() => {
    return {
      type: CONTENT_TYPE,
      text: text.value
    }
  })

  const effectiveTitle = usePreviewWidgetTitle(
    computed(() => {
      return {
        generalSettings: widgetGeneralSettings.value,
        content: content.value,
        effectiveFilters: {}
      }
    })
  )

  const widgetProps = ref<WidgetProps>(_buildWidgetProps())

  function _buildWidgetProps(): WidgetProps {
    return {
      general_settings: widgetGeneralSettings.value,
      content: content.value,
      effectiveTitle: effectiveTitle.value,
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

    text,

    widgetProps
  }
}
