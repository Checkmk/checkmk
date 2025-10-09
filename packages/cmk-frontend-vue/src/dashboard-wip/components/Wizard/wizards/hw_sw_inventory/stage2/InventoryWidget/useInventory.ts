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
  InventoryContent,
  UseValidate,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

type ToggleFunction = (value: boolean) => void

export interface UseInventory extends UseWidgetHandler, UseWidgetVisualizationOptions, UseValidate {
  toggleTitleUrl: ToggleFunction

  //Inventory
  inventoryPath: Ref<string | null>

  //Validation
  titleUrlValidationErrors: Ref<string[]>
}

export const useInventory = (
  filters: ConfiguredFilters,
  editWidget: WidgetProps | null = null
): UseInventory => {
  const content = editWidget?.content as InventoryContent | undefined
  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    widgetGeneralSettings,
    generateTitleSpec
  } = useWidgetVisualizationProps('Inventory', editWidget?.general_settings)

  const inventoryPath = ref<string | null>(content?.path ?? null)

  const _generateWidgetProps = (): WidgetProps => {
    const content: InventoryContent = {
      type: 'inventory',
      path: inventoryPath.value ?? ''
    }

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [widgetGeneralSettings, inventoryPath],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

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

    titleUrlValidationErrors,
    validate,

    widgetProps
  }
}
