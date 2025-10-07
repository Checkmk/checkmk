/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  HostStatisticsContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

export interface UseHostStatistics extends UseWidgetHandler, UseWidgetVisualizationOptions {}

export const useHostStatistics = (filters: ConfiguredFilters): UseHostStatistics => {
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

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: HostStatisticsContent = {
      type: 'host_stats'
    }

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [title, showTitle, showTitleBackground, titleUrlEnabled, titleUrl],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
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
