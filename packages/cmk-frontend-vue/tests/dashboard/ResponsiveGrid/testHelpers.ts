/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type {
  ContentResponsiveGrid,
  DashboardConstants,
  ResponsiveGridBreakpoint
} from '@/dashboard/types/dashboard'
import type { ResponsiveGridWidget } from '@/dashboard/types/widget'

export const breakpointSettings: DashboardConstants['responsive_grid_breakpoints'] = {
  XS: { min_width: 280, columns: 4 },
  S: { min_width: 535, columns: 8 },
  M: { min_width: 705, columns: 12 },
  L: { min_width: 961, columns: 12 },
  XL: { min_width: 1217, columns: 24 }
}

export const widgetConstraints: DashboardConstants['widgets'] = {}

export function makeContentProps(id?: string): ContentProps {
  return {
    widget_id: id ?? 'test-widget',
    general_settings: {
      title: { text: 'Test', render_mode: 'with_background' },
      render_background: true
    },
    content: { type: 'static_text', text: 'example' },
    effectiveTitle: 'Test',
    effective_filter_context: {
      uses_infos: [],
      filters: {},
      restricted_to_single: []
    },
    dashboardKey: { owner: 'admin', name: 'test' }
  }
}

export function makeLayoutWidget(
  layouts: Record<
    string,
    Record<string, { position: { x: number; y: number }; size: { columns: number; rows: number } }>
  >
): ResponsiveGridWidget {
  return {
    content: { type: 'static_text', text: 'example' },
    layout: { type: 'responsive_grid', layouts },
    general_settings: {
      title: { text: 'title', render_mode: 'with_background' },
      render_background: true
    },
    filter_context: {
      uses_infos: [],
      filters: {}
    }
  }
}

export function makeRGContent(
  widgets: Record<string, ResponsiveGridWidget>,
  layoutBreakpoints: ResponsiveGridBreakpoint[] = ['L', 'XL'],
  layouts?: Record<string, { title: string; breakpoints: ResponsiveGridBreakpoint[] }>
): ContentResponsiveGrid {
  return {
    layout: {
      type: 'responsive_grid',
      layouts: layouts ?? {
        default: { title: 'Default', breakpoints: layoutBreakpoints }
      }
    },
    widgets
  }
}
