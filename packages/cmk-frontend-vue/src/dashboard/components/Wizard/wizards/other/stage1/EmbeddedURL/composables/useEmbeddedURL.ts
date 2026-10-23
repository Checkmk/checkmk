/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { useDebounceRef } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, computed, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { URLContent, UseWidgetHandler, WidgetProps } from '@/dashboard/components/Wizard/types'
import { isUrl } from '@/dashboard/components/Wizard/utils'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard/utils'

const { _t } = usei18n()

const CONTENT_TYPE = 'url'
export interface UseEmbeddedURL extends UseWidgetHandler, UseWidgetVisualizationOptions {
  url: Ref<string>
  urlValidationErrors: Ref<string[]>
  includeContext: Ref<boolean>
  includeTimeRange: Ref<boolean>
}

export function useEmbeddedURL(currentSpec: WidgetSpec | null): UseEmbeddedURL {
  const constants = useInjectDashboardConstants()
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
  } = useWidgetVisualizationProps('$DEFAULT_TITLE$', currentSpec?.general_settings, CONTENT_TYPE)

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE ? (currentSpec?.content as URLContent) : undefined

  const url = ref(currentContent?.url || '')
  const urlValidationErrors = ref<string[]>([])
  const includeContext = ref(currentContent?.include_context ?? false)
  const includeTimeRange = ref(currentContent?.include_time_range ?? false)

  const content = computed<URLContent>(() => {
    return {
      type: CONTENT_TYPE,
      url: url.value,
      include_context: includeContext.value,
      include_time_range: includeTimeRange.value
    }
  })
  const debouncedContent = useDebounceRef(content, 300)

  function validateUrl(): boolean {
    urlValidationErrors.value = isUrl(url.value) ? [] : [_t('Value must be a valid URL')]
    return urlValidationErrors.value.length === 0
  }

  function validate(): boolean {
    const isUrlValid = validateUrl()
    const isVisualizationValid = validateVisualization()
    return isUrlValid && isVisualizationValid
  }

  watch(url, () => {
    urlValidationErrors.value = []
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
      content: debouncedContent.value,
      effectiveTitle: effectiveTitle.value,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content.value,
        {},
        [], // we know this doesn't use any infos, no need to ask the backend
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

    url,
    urlValidationErrors,
    includeContext,
    includeTimeRange,

    widgetProps,
    getSubmitProps: async () => widgetProps.value
  }
}
