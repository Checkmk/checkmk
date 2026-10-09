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
import { useDataRangeInput } from '@/dashboard/components/Wizard/components/DataRangeInput/useDataRangeInput'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  BarplotContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

type DataRangeType = 'fixed' | 'automatic'

const CONTENT_TYPE = 'barplot'

export interface UseBarplot extends UseWidgetHandler, UseWidgetVisualizationOptions {
  contextualLink: UseContextualLink<BarplotContent>
  //Data settings
  dataRangeType: Ref<DataRangeType>
  dataRangeSymbol: Ref<string>
  dataRangeMin: Ref<number>
  dataRangeMax: Ref<number>
}

export const useBarplot = async (
  metric: string,
  filters: ConfiguredFilters,
  currentSpec?: WidgetSpec | null
): Promise<UseBarplot> => {
  const constants = useInjectDashboardConstants()
  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE ? (currentSpec?.content as BarplotContent) : null

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    titleMacros,
    validate: validateTitle,
    widgetGeneralSettings
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings, CONTENT_TYPE)

  const {
    type: dataRangeType,
    symbol,
    maximum,
    minimum,
    dataRangeProps
  } = useDataRangeInput(currentContent?.display_range)

  const contextualLink = useContextualLink<BarplotContent>(
    constants.widgets[CONTENT_TYPE]!.contextual_link!,
    currentContent?.contextual_link
  )

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    const isTitleValid = validateTitle()
    const isLinkValid = contextualLink.validate()
    return isTitleValid && isLinkValid
  }

  const _generateContent = (): BarplotContent => {
    return {
      type: CONTENT_TYPE,
      metric: metric,
      display_range: dataRangeProps.value,
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
    [contextualLink.contextualLink, widgetGeneralSettings, dataRangeProps],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    contextualLink,

    dataRangeType,
    dataRangeSymbol: symbol,
    dataRangeMin: minimum,
    dataRangeMax: maximum,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    titleMacros,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>,
    getSubmitProps: _computeWidgetProps
  }
}
