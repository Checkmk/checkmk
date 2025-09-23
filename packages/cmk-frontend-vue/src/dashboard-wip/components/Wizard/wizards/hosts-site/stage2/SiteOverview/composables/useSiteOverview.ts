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
  SiteOverviewContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

export interface UseSiteOverview extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  showStateOf: Ref<string>
  hexagonSize: Ref<string>
}

export const useSiteOverview = (filters: ConfiguredFilters): UseSiteOverview => {
  //Todo: Fill values if they exist in serializedData
  const showStateOf = ref<'via_context' | 'sites' | 'hosts'>('via_context')
  const hexagonSize = ref<string>('small')

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
    const content: SiteOverviewContent = {
      type: 'site_overview',
      dataset: showStateOf.value,
      hexagon_size: hexagonSize.value === 'small' ? 'default' : 'large'
    }

    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [title, showTitle, showTitleBackground, titleUrlEnabled, titleUrl, showStateOf, hexagonSize],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

  return {
    showStateOf,
    hexagonSize,

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
