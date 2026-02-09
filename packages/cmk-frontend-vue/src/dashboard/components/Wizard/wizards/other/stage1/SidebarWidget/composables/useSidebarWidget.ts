/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, onBeforeMount, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { UseWidgetHandler, WidgetProps } from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { SidebarElementContent, WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext, dashboardAPI } from '@/dashboard/utils'

import type { UseSidebarElements } from './useSidebarElements'

const CONTENT_TYPE = 'sidebar_element'

export interface UseSidebarWidget extends UseWidgetHandler, UseWidgetVisualizationOptions {
  sidebarElementName: Ref<string>
}

export function useSidebarWidget(
  sidebarElements: UseSidebarElements['elements'],
  currentSpec: WidgetSpec | null
): UseSidebarWidget {
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
      ? (currentSpec?.content as SidebarElementContent)
      : undefined
  const elementName = ref<string>(currentContent?.name || 'tactical_overview')

  watch(sidebarElements, (newElements) => {
    // update the selected element, if the current one is not available anymore
    if (newElements.length === 0) {
      return
    }
    if (!newElements.some((el) => el.id === elementName.value)) {
      elementName.value = newElements[0]!.id
    }
  })

  const content = computed<SidebarElementContent>(() => {
    return {
      type: CONTENT_TYPE,
      name: elementName.value
    }
  })

  const usesInfos = ref<string[]>([])
  onBeforeMount(async () => {
    const resp = await dashboardAPI.computeWidgetAttributes(content.value)
    usesInfos.value = resp.value.filter_context.uses_infos
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

  const widgetProps = computed<WidgetProps>(() => {
    return {
      general_settings: widgetGeneralSettings.value,
      content: content.value,
      effectiveTitle: effectiveTitle.value,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content.value,
        {},
        usesInfos.value,
        constants
      )
    }
  })

  function validate(): boolean {
    const validElementName = sidebarElements.value.some((el) => el.id === elementName.value)
    return validElementName && validateTitle()
  }

  return {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    titleMacros,
    validate,

    sidebarElementName: elementName,

    widgetProps
  }
}
