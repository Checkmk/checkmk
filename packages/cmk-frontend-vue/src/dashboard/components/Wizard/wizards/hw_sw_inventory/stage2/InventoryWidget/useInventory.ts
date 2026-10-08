/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, ref, watch } from 'vue'

import {
  type UseContextualLink,
  useContextualLink
} from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  InventoryContent,
  UseValidate,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

type ToggleFunction = (value: boolean) => void

const CONTENT_TYPE = 'inventory'
export interface UseInventory extends UseWidgetHandler, UseWidgetVisualizationOptions, UseValidate {
  toggleTitleUrl: ToggleFunction
  contextualLink: UseContextualLink<InventoryContent>

  //Validation
  titleUrlValidationErrors: Ref<string[]>
}

export const useInventory = async (
  inventoryPath: Ref<string | null>,
  filters: ConfiguredFilters,
  editWidget: WidgetProps | null = null
): Promise<UseInventory> => {
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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', editWidget?.general_settings, CONTENT_TYPE)

  const contextualLink = useContextualLink<InventoryContent>(
    constants.widgets[CONTENT_TYPE]!.contextual_link!,
    editWidget?.content?.type === CONTENT_TYPE ? editWidget.content.contextual_link : undefined
  )

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    const isTitleValid = validateTitle()
    const isLinkValid = contextualLink.validate()

    return isTitleValid && isLinkValid
  }

  const _generateContent = (): InventoryContent => {
    return {
      type: CONTENT_TYPE,
      path: inventoryPath.value ?? '',
      contextual_link: contextualLink.contextualLink.value ?? { type: 'default' }
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
    [widgetGeneralSettings, inventoryPath, contextualLink.contextualLink, showWidgetBackground],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  const toggleTitleUrl = (value: boolean) => {
    titleUrl.value = ''
    titleUrlEnabled.value = value
  }

  return {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,

    titleUrlEnabled,
    titleUrl,
    toggleTitleUrl,
    titleMacros,

    contextualLink,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>,
    getSubmitProps: _computeWidgetProps
  }
}
