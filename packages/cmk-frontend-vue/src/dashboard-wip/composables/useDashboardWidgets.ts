/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import type {
  RelativeGridWidgets,
  ResponsiveGridWidgets,
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetLayout
} from '@/dashboard-wip/types/widget'
import type { AnyWidget } from '@/dashboard-wip/types/widget'

export interface WidgetCore {
  widget_id: string
  general_settings: WidgetGeneralSettings
  content: WidgetContent
  filter_context: WidgetFilterContext
}

export function useDashboardWidgets(
  widgetsRef: Ref<RelativeGridWidgets | ResponsiveGridWidgets | undefined>
) {
  const widgetCores = computed<Record<string, WidgetCore>>(() => {
    const widgets = widgetsRef.value
    if (!widgets) {
      return {}
    }
    const record: Record<string, WidgetCore> = {}
    for (const [widgetId, widget] of Object.entries(widgets)) {
      record[widgetId] = {
        widget_id: widgetId,
        general_settings: widget.general_settings,
        filter_context: widget.filter_context,
        content: widget.content
      }
    }
    return record
  })

  function getWidget(widgetId: string): WidgetCore | null {
    return widgetCores.value[widgetId] || null
  }

  function addWidget(
    id: string,
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext,
    layout: WidgetLayout
  ) {
    const widgets = widgetsRef.value
    if (!widgets) {
      throw new Error('Cannot add widget: widgetsRef is undefined')
    }
    if (widgets[id]) {
      throw new Error(`Widget with ID '${id}' already exists`)
    }

    widgets[id] = {
      general_settings: generalSettings,
      content,
      filter_context: filterContext,
      layout
    } as AnyWidget
  }

  function cloneWidget(oldId: string, newId: string, layout: WidgetLayout) {
    const widgets = widgetsRef.value
    if (!widgets) {
      throw new Error('Cannot add widget: widgetsRef is undefined')
    }
    if (!widgets[oldId]) {
      throw new Error(`Widget with ID '${oldId}' doesn't exist`)
    }
    if (widgets[newId]) {
      throw new Error(`Widget with ID '${newId}' already exists`)
    }

    const widget: AnyWidget = structuredClone(widgets[oldId])
    widget.layout = layout

    widgets[newId] = widget
  }

  function deleteWidget(widgetId: string) {
    const widgets = widgetsRef.value
    if (!widgets) {
      throw new Error('Cannot delete widget: widgetsRef is undefined')
    }
    if (widgets[widgetId]) {
      delete widgets[widgetId]
    }
  }

  function updateWidget(
    id: string,
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ) {
    const widgets = widgetsRef.value
    if (!widgets) {
      throw new Error('Cannot add widget: widgetsRef is undefined')
    }
    if (!widgets[id]) {
      throw new Error(`Widget with ID '${id}' does not exist. This should not happen`)
    }

    widgets[id] = {
      general_settings: generalSettings,
      content,
      filter_context: filterContext,
      layout: widgets[id]!.layout
    } as AnyWidget
  }

  return {
    widgetCores,
    getWidget,
    addWidget,
    updateWidget,
    cloneWidget,
    deleteWidget
  }
}

export type DashboardWidgets = ReturnType<typeof useDashboardWidgets>
