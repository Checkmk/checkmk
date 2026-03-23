/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ContentRelativeGrid } from '@/dashboard/types/dashboard'
import type { RelativeGridWidget, WidgetSizeValue } from '@/dashboard/types/widget'

export function makeRelativeGridWidget(
  overrides: {
    position?: { x: number; y: number }
    size?: { width: WidgetSizeValue; height: WidgetSizeValue }
    render_mode?: 'hidden' | 'with_background' | 'without_background'
  } = {}
): RelativeGridWidget {
  return {
    content: { type: 'static_text', text: 'example' },
    general_settings: {
      title: {
        text: 'Test Widget',
        render_mode: overrides.render_mode ?? 'with_background'
      },
      render_background: true
    },
    filter_context: {
      uses_infos: [],
      filters: {}
    },
    layout: {
      type: 'relative_grid',
      position: overrides.position ?? { x: 1, y: 1 },
      size: overrides.size ?? { width: 20, height: 10 }
    }
  }
}

export function makeRelativeGridContent(
  widgets: Record<string, RelativeGridWidget> = {}
): ContentRelativeGrid {
  return {
    layout: { type: 'relative_grid' },
    widgets
  }
}

export const STANDARD_DASHBOARD_DIMS = { width: 1000, height: 800 }
