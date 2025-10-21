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
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard-wip/utils'

export interface UseSiteOverview extends UseWidgetHandler, UseWidgetVisualizationOptions {
  //Data settings
  showStateOf: Ref<string>
  hexagonSize: Ref<string>
}

export const useSiteOverview = async (
  filters: ConfiguredFilters,
  dashboardConstants: DashboardConstants,
  currentSpec?: WidgetSpec | null
): Promise<UseSiteOverview> => {
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
    widgetGeneralSettings
  } = useWidgetVisualizationProps('', currentSpec?.general_settings)

  const currentContent = currentSpec?.content as SiteOverviewContent

  const showStateOf = ref<'via_context' | 'sites' | 'hosts'>(
    currentContent?.dataset ?? 'via_context'
  )
  const hexagonSize = ref<string>(currentContent?.hexagon_size ?? 'small')
  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateContent = (): SiteOverviewContent => {
    return {
      type: 'site_overview',
      dataset: showStateOf.value,
      hexagon_size: hexagonSize.value === 'small' ? 'default' : 'large'
    }
  }

  const _updateWidgetProps = async () => {
    const content = _generateContent()
    widgetProps.value = {
      general_settings: widgetGeneralSettings.value,
      content,
      effective_filter_context: await determineWidgetEffectiveFilterContext(
        content,
        filters,
        dashboardConstants
      )
    }
  }

  watch(
    [widgetGeneralSettings, showStateOf, hexagonSize],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

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

    widgetProps: widgetProps as Ref<WidgetProps>
  }
}
