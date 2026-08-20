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
import type { NetworkFlowDonutContent, WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard/utils'

const CONTENT_TYPE = 'network_flow_donut'

export const MAX_SLICES = 20

type Dimension = NetworkFlowDonutContent['dimension']
type LegendMode = NetworkFlowDonutContent['legend_mode']

export interface UseDonut extends UseWidgetHandler, UseWidgetVisualizationOptions {
  dimension: Ref<Dimension>
  limitTo: Ref<number>
  limitToValidationErrors: Ref<string[]>
  legendMode: Ref<LegendMode>
}

export function useDonut(currentSpec: WidgetSpec | null): UseDonut {
  const { _t } = usei18n()
  const constants = useInjectDashboardConstants()

  // Default widget title per dimension; mirrors the dimension dropdown labels.
  const dimensionTitles: Record<Dimension, string> = {
    applications: _t('Applications'),
    protocols: _t('Protocols')
  }

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as NetworkFlowDonutContent)
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
  const limitTo = ref<number>(currentContent?.limit_to ?? 6)
  const limitToValidationErrors = ref<string[]>([])
  const legendMode = ref<LegendMode>(currentContent?.legend_mode ?? 'table')

  // Unless the user has customized the title, keep it in sync with the
  // dimension's default as the dimension changes.
  watch(dimension, (newDimension, oldDimension) => {
    if (title.value === dimensionTitles[oldDimension]) {
      title.value = dimensionTitles[newDimension]
    }
  })

  function validate(): boolean {
    limitToValidationErrors.value = []
    if (limitTo.value < 1 || limitTo.value > MAX_SLICES) {
      limitToValidationErrors.value.push(`1 - ${MAX_SLICES}`)
    }
    return validateVisualization() && limitToValidationErrors.value.length === 0
  }

  const content = computed<NetworkFlowDonutContent>(() => {
    return {
      type: CONTENT_TYPE,
      dimension: dimension.value,
      limit_to: limitTo.value,
      legend_mode: legendMode.value
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
    limitTo,
    limitToValidationErrors,
    legendMode,

    widgetProps,
    getSubmitProps: async () => widgetProps.value
  }
}
