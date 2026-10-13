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
  HostStateContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { computePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { determineWidgetEffectiveFilterContext } from '@/dashboard/utils'

const CONTENT_TYPE = 'host_state'
export interface UseHostState extends UseWidgetHandler, UseWidgetVisualizationOptions {
  contextualLink: UseContextualLink<HostStateContent>
  //Data settings
  showBackgroundInStatusColorAndLabel: Ref<boolean>
  colorizeStates: Ref<string>
  showSummaryForNonUpStates: Ref<boolean>
}

export const useHostState = async (
  filters: ConfiguredFilters,
  currentSpec?: WidgetSpec | null
): Promise<UseHostState> => {
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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings, CONTENT_TYPE)

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE ? (currentSpec?.content as HostStateContent) : null

  const contextualLink = useContextualLink<HostStateContent>(
    constants.widgets[CONTENT_TYPE]!.contextual_link!,
    currentContent?.contextual_link
  )

  const showBackgroundInStatusColorAndLabel = ref<boolean>(!!currentContent?.status_display)
  const colorizeStates = ref<string>(currentContent?.status_display?.for_states ?? 'all')
  const showSummaryForNonUpStates = ref<boolean>(currentContent?.show_summary === 'not_ok')

  const widgetProps = ref<WidgetProps>()

  const validate = (): boolean => {
    const isTitleValid = validateTitle()
    const isLinkValid = contextualLink.validate()
    return isTitleValid && isLinkValid
  }

  const _generateContent = (): HostStateContent => {
    const content: HostStateContent = {
      type: CONTENT_TYPE,
      contextual_link: contextualLink.contextualLink.value ?? { type: 'default' }
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

    return content
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
    [
      contextualLink.contextualLink,
      widgetGeneralSettings,
      showBackgroundInStatusColorAndLabel,
      colorizeStates,
      showSummaryForNonUpStates
    ],
    useDebounceFn(() => {
      void _updateWidgetProps()
    }, 300),
    { deep: true }
  )

  await _updateWidgetProps()

  return {
    contextualLink,

    showBackgroundInStatusColorAndLabel,
    colorizeStates,
    showSummaryForNonUpStates,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleMacros,

    titleUrlValidationErrors,
    validate,

    widgetProps: widgetProps as Ref<WidgetProps>,
    getSubmitProps: _computeWidgetProps
  }
}
