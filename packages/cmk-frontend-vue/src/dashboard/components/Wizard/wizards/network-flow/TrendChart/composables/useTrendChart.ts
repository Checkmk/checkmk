/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { UseWidgetHandler, WidgetProps } from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { NetworkFlowTrendChartContent, WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard/utils'

const CONTENT_TYPE = 'network_flow_trend_chart'

export const MAX_SERIES = 10

type Dimension = NetworkFlowTrendChartContent['dimension']
type DisplayMode = NetworkFlowTrendChartContent['display_mode']

export interface UseTrendChart extends UseWidgetHandler, UseWidgetVisualizationOptions {
  dimension: Ref<Dimension>
  displayMode: Ref<DisplayMode>
  limitTo: Ref<number>
  limitToValidationErrors: Ref<string[]>
  showLegend: Ref<boolean>
}

export function useTrendChart(currentSpec: WidgetSpec | null): UseTrendChart {
  const { _t } = usei18n()
  const constants = useInjectDashboardConstants()

  // Default widget title per dimension; mirrors the dimension dropdown labels
  // and the flow monitoring mockups.
  const dimensionTitles: Record<Dimension, string> = {
    applications: _t('Top applications'),
    autonomous_systems: _t('Top active ASN'),
    total_bandwidth: _t('Total bandwidth')
  }

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as NetworkFlowTrendChartContent)
      : undefined
  const initialDimension: Dimension = currentContent?.dimension ?? 'applications'

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateVisualization,
    widgetGeneralSettings,
    titleMacros
  } = useWidgetVisualizationProps(
    dimensionTitles[initialDimension],
    currentSpec?.general_settings,
    CONTENT_TYPE
  )

  const dimension = ref<Dimension>(initialDimension)
  const displayMode = ref<DisplayMode>(currentContent?.display_mode ?? 'stacked_area')
  const limitTo = ref<number>(currentContent?.limit_to ?? 6)
  const limitToValidationErrors = ref<string[]>([])
  const showLegend = ref<boolean>(currentContent?.show_legend ?? true)

  // Unless the user has customized the title, keep it in sync with the
  // dimension's default as the dimension changes.
  watch(dimension, (newDimension, oldDimension) => {
    if (title.value === dimensionTitles[oldDimension]) {
      title.value = dimensionTitles[newDimension]
    }
  })

  function validate(): boolean {
    limitToValidationErrors.value = []
    // Total bandwidth is a fixed two-series view; the top-N limit does not apply.
    if (
      dimension.value !== 'total_bandwidth' &&
      (limitTo.value < 1 || limitTo.value > MAX_SERIES)
    ) {
      limitToValidationErrors.value.push(`1 - ${MAX_SERIES}`)
    }
    return validateVisualization() && limitToValidationErrors.value.length === 0
  }

  const content = computed<NetworkFlowTrendChartContent>(() => {
    return {
      type: CONTENT_TYPE,
      dimension: dimension.value,
      display_mode: displayMode.value,
      limit_to: limitTo.value,
      show_legend: showLegend.value
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

  const widgetProps = computed<WidgetProps>(() => {
    return {
      general_settings: widgetGeneralSettings.value,
      content: content.value,
      effectiveTitle: effectiveTitle.value,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content.value,
        {},
        [], // filters are not wired into the flow queries yet
        constants
      )
    }
  })

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

    dimension,
    displayMode,
    limitTo,
    limitToValidationErrors,
    showLegend,

    widgetProps,
    getSubmitProps: async () => widgetProps.value
  }
}
