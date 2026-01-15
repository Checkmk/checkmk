/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import {
  type UseLinkContent,
  useLinkContent
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useLinkContent'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  InventoryContent,
  InventoryLinkType,
  UseValidate,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

type ToggleFunction = (value: boolean) => void

const CONTENT_TYPE = 'inventory'
export interface UseInventory
  extends UseWidgetHandler,
    UseWidgetVisualizationOptions,
    UseLinkContent,
    UseValidate {
  toggleTitleUrl: ToggleFunction

  //Inventory
  inventoryPath: Ref<string | null>

  //Validation
  titleUrlValidationErrors: Ref<string[]>
}

export const useInventory = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  editWidget: WidgetProps | null = null
): Promise<UseInventory> => {
  const content =
    editWidget?.content?.type === CONTENT_TYPE
      ? (editWidget?.content as InventoryContent)
      : undefined
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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', editWidget?.general_settings)

  const inventoryPath = ref<string | null>(content?.path ?? null)

  const {
    linkType,
    linkTarget,
    linkValidationError,
    linkTargetSuggestions,
    validate: validateLinkContent
  } = useLinkContent()

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    const isTitleValid = validateTitle()
    const isLinkValid = validateLinkContent()

    return isTitleValid && isLinkValid
  }

  const _generateContent = (): InventoryContent => {
    const content: InventoryContent = {
      type: CONTENT_TYPE,
      path: inventoryPath.value ?? ''
    }

    if (linkType.value && linkTarget.value) {
      content.link_spec = {
        type: linkType.value as InventoryLinkType,
        name: linkTarget.value
      }
    }

    return content
  }

  const _updateWidgetProps = async () => {
    const content = _generateContent()
    const [effectiveTitle, effectiveFilterContext] = await Promise.all([
      computePreviewWidgetTitle({
        generalSettings: widgetGeneralSettings.value,
        content,
        effectiveFilters: filters
      }),
      determineWidgetEffectiveFilterContext(content, filters, dashboardConstants)
    ])

    widgetProps.value = {
      general_settings: widgetGeneralSettings.value,
      content,
      effectiveTitle,
      effective_filter_context: effectiveFilterContext
    }
  }

  watch(
    [widgetGeneralSettings, inventoryPath, linkType, linkTarget],
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

    inventoryPath,

    linkType,
    linkTarget,
    linkValidationError,
    linkTargetSuggestions,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
