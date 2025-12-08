/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, onBeforeMount, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { UseWidgetHandler, WidgetProps } from '@/dashboard-wip/components/Wizard/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { SidebarElementContent, WidgetSpec } from '@/dashboard-wip/types/widget'
import { buildWidgetEffectiveFilterContext, dashboardAPI } from '@/dashboard-wip/utils'

import type { UseSidebarElements } from './useSidebarElements'

const CONTENT_TYPE = 'sidebar_element'

export interface UseSidebarWidget extends UseWidgetHandler, UseWidgetVisualizationOptions {
  sidebarElementName: Ref<string>
}

export function useSidebarWidget(
  sidebarElements: UseSidebarElements['elements'],
  dashboardConstants: DashboardConstants,
  currentSpec: WidgetSpec | null
): UseSidebarWidget {
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
    if (title.value === '') {
      const defaultTitle = newElements.find((el) => el.id === elementName.value)?.title
      if (defaultTitle) {
        title.value = defaultTitle
      }
    }
  })

  watch([title, elementName], ([newTitle, newElementName], [oldTitle, oldElementName]) => {
    // if the user has not customized the title (or it's empty), update it when the element changes
    if (oldTitle !== newTitle) {
      return
    }
    const oldDefaultTitle = sidebarElements.value.find((el) => el.id === oldElementName)?.title
    if (newTitle === oldDefaultTitle || newTitle === '') {
      const newDefaultTitle = sidebarElements.value.find((el) => el.id === newElementName)?.title
      if (newDefaultTitle) {
        title.value = newDefaultTitle
      }
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

  const widgetProps = ref<WidgetProps>(_buildWidgetProps())

  function _buildWidgetProps(): WidgetProps {
    return {
      general_settings: widgetGeneralSettings.value,
      content: content.value,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content.value,
        {},
        usesInfos.value,
        dashboardConstants
      )
    }
  }
  watch(
    [widgetGeneralSettings, usesInfos, content],
    useDebounceFn(() => {
      widgetProps.value = _buildWidgetProps()
    }, 300),
    { deep: true }
  )

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
    validate,

    sidebarElementName: elementName,

    widgetProps
  }
}
