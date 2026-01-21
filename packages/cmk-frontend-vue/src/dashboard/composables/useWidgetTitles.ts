/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { ComputeWidgetTitlesRequest, ComputeWidgetTitlesResponse } from '@/dashboard/types/api'

import type { WidgetContent, WidgetGeneralSettings } from '../types/widget'
import { dashboardAPI } from '../utils'
import type { DashboardFilters } from './useDashboardFilters'
import type { DashboardWidgets } from './useDashboardWidgets'
import { useDebounceRef } from './useDebounce'

export type WidgetTitles = ComputeWidgetTitlesResponse['extensions']['titles']

export function useComputeWidgetTitles(
  baseFilters: DashboardFilters['baseFilters'],
  widgetCores: DashboardWidgets['widgetCores']
) {
  const widgetTitles = ref<WidgetTitles>({})

  async function computeTitles() {
    if (Object.keys(widgetCores.value).length === 0) {
      widgetTitles.value = {}
      return
    }
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
    const response = await dashboardAPI.computeWidgetTitles({
      widgets
    })
    widgetTitles.value = response.extensions.titles
  }

  watch(
    [widgetCores, baseFilters],
    () => {
      void computeTitles()
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
