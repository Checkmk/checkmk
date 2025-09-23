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
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

export interface UseHostState extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  showBackgroundInStatusColorAndLabel: Ref<boolean>
  colorizeStates: Ref<string>
  showSummaryForNonUpStates: Ref<boolean>
}

export const useHostState = (filters: ConfiguredFilters): UseHostState => {
  //Todo: Fill values if they exist in serializedData
  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    generateTitleSpec
  } = useWidgetVisualizationProps('')

  const showBackgroundInStatusColorAndLabel = ref<boolean>(true)
  const colorizeStates = ref<string>('all')
  const showSummaryForNonUpStates = ref<boolean>(false)

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
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

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [
      title,
      showTitle,
      showTitleBackground,
      titleUrlEnabled,
      titleUrl,
      showBackgroundInStatusColorAndLabel,
      colorizeStates,
      showSummaryForNonUpStates
    ],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

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

    widgetProps
  }
}
