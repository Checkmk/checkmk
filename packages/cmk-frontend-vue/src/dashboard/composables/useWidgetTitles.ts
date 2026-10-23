/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useDebounceRef } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, computed, ref, watch } from 'vue'

import type { ComputeWidgetTitlesRequest, ComputeWidgetTitlesResponse } from '@/dashboard/types/api'

import type { WidgetContent, WidgetGeneralSettings } from '../types/widget'
import { dashboardAPI } from '../utils'
import type { DashboardFilters } from './useDashboardFilters'
import type { DashboardWidgets } from './useDashboardWidgets'

export type WidgetTitles = ComputeWidgetTitlesResponse['extensions']['titles']

export function useComputeWidgetTitles(
  baseFilters: DashboardFilters['baseFilters'],
  widgetCores: DashboardWidgets['widgetCores']
) {
  const widgetTitles = ref<WidgetTitles>({})

  const request = computed<ComputeWidgetTitlesRequest>(() => {
    const widgets: ComputeWidgetTitlesRequest['widgets'] = {}
    for (const [widgetId, widget] of Object.entries(widgetCores.value)) {
      widgets[widgetId] = {
        general_settings: widget.general_settings,
        content: widget.content,
        filters: {
          ...baseFilters.value,
          ...widget.filter_context.filters
        }
      }
    }
    return { widgets }
  })
  // The sources hand out a new object on every recompute, so compare what we would send.
  const requestKey = computed<string>(() => JSON.stringify(request.value))
  // One operation changes widgets and filters a microtask apart; that must not be two requests.
  const debouncedRequestKey = useDebounceRef(requestKey, 50)

  watch(
    debouncedRequestKey,
    async () => {
      const payload = request.value
      const key = requestKey.value
      if (Object.keys(payload.widgets).length === 0) {
        widgetTitles.value = {}
        return
      }
      try {
        const response = await dashboardAPI.computeWidgetTitles(payload)
        if (requestKey.value !== key) {
          // A newer request is already on its way.
          return
        }
        widgetTitles.value = response.extensions.titles
      } catch (error) {
        console.error('Error computing widget titles:', error)
      }
    },
    { immediate: true }
  )

  return widgetTitles
}

export interface PreviewTitleProps {
  generalSettings: WidgetGeneralSettings
  content: WidgetContent
  effectiveFilters: {
    [key: string]: {
      [key: string]: string
    }
  }
}
/**
 * Computes the title for a single widget.
 * This function expects the dashboard filters to be already merged into the widget's filter context.
 * @param widget - The widget data
 */
export async function computePreviewWidgetTitle(
  widget: PreviewTitleProps
): Promise<string | undefined> {
  const WIDGET_ID = 'preview_widget'
  const response = await dashboardAPI.computeWidgetTitles({
    widgets: {
      [WIDGET_ID]: {
        general_settings: widget.generalSettings,
        content: widget.content,
        filters: widget.effectiveFilters
      }
    }
  })
  return response.extensions.titles[WIDGET_ID]
}

export function usePreviewWidgetTitle(widget: Ref<PreviewTitleProps>) {
  const previewTitle = ref<string | undefined>()
  const debounced = useDebounceRef(widget, 300, true)
  watch(
    debounced,
    () => {
      void computePreviewWidgetTitle(debounced.value).then((title) => {
        previewTitle.value = title
      })
    },
    { immediate: true }
  )
  return previewTitle
}
