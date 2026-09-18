/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { createWidgetLayout } from '@/dashboard/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import { defaultResponsiveGridLayout } from '@/dashboard/components/ResponsiveGrid/composables/utils'
import type {
  ContentRelativeGrid,
  ContentResponsiveGrid,
  DashboardConstants
} from '@/dashboard/types/dashboard'
import type { ResponsiveGridWidget, ResponsiveGridWidgetLayouts } from '@/dashboard/types/widget'

/**
 * Place the widgets on a responsive grid in the given order, using the packer that also places a
 * hand-added widget, so the result matches adding them one by one. Widgets the API cannot
 * represent are left out and take up no space.
 */
export function buildResponsiveWidgetLayouts(
  readingOrder: string[],
  relativeContent: ContentRelativeGrid,
  constants: DashboardConstants
): Record<string, ResponsiveGridWidgetLayouts> {
  const placedContent: ContentResponsiveGrid = {
    layout: defaultResponsiveGridLayout(),
    widgets: {}
  }
  const widgetLayouts: Record<string, ResponsiveGridWidgetLayouts> = {}

  for (const widgetId of readingOrder) {
    const widget = relativeContent.widgets[widgetId]
    if (!widget) {
      throw new Error(`Widget with ID '${widgetId}' does not exist`)
    }
    if (widget.content.type === 'not_supported') {
      continue
    }

    const layout = createWidgetLayout(placedContent, widget.content.type, constants)
    widgetLayouts[widgetId] = layout
    placedContent.widgets[widgetId] = { ...widget, layout } as ResponsiveGridWidget
  }

  return widgetLayouts
}
