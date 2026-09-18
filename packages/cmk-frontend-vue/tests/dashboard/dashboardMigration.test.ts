/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { createWidgetLayout } from '@/dashboard/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import { defaultResponsiveGridLayout } from '@/dashboard/components/ResponsiveGrid/composables/utils'
import { buildResponsiveWidgetLayouts } from '@/dashboard/dashboardMigration'
import type {
  ContentRelativeGrid,
  DashboardConstants,
  ResponsiveGridBreakpoint
} from '@/dashboard/types/dashboard'
import type {
  RelativeGridWidget,
  ResponsiveGridWidgetLayout,
  ResponsiveGridWidgetLayouts,
  WidgetContent
} from '@/dashboard/types/widget'

const WIDGET_TYPE = 'static_text'

const constants: DashboardConstants = {
  responsive_grid_breakpoints: {
    XS: { min_width: 280, columns: 4 },
    S: { min_width: 535, columns: 8 },
    M: { min_width: 705, columns: 12 },
    L: { min_width: 961, columns: 12 },
    XL: { min_width: 1217, columns: 24 }
  },
  widgets: {
    [WIDGET_TYPE]: {
      filter_context: { restricted_to_single: [] },
      title_macros: [],
      layout: {
        relative: {
          initial_size: { width: 1, height: 1 },
          minimum_size: { width: 1, height: 1 },
          initial_position: { x: 1, y: 1 },
          is_resizable: true
        },
        responsive: {
          XS: { minimum_size: { columns: 2, rows: 2 }, initial_size: { columns: 4, rows: 4 } },
          S: { minimum_size: { columns: 2, rows: 2 }, initial_size: { columns: 4, rows: 4 } },
          M: { minimum_size: { columns: 2, rows: 2 }, initial_size: { columns: 4, rows: 4 } },
          L: { minimum_size: { columns: 2, rows: 2 }, initial_size: { columns: 4, rows: 4 } },
          XL: { minimum_size: { columns: 2, rows: 3 }, initial_size: { columns: 6, rows: 5 } }
        }
      }
    }
  }
}

const declaredBreakpoints = defaultResponsiveGridLayout().layouts['default']!
  .breakpoints as ResponsiveGridBreakpoint[]

function makeRelativeWidget(content: WidgetContent): RelativeGridWidget {
  return {
    content,
    general_settings: {
      title: { text: 'Test Widget', render_mode: 'with_background' },
      render_background: true
    },
    filter_context: { uses_infos: [], filters: {} },
    layout: {
      type: 'relative_grid',
      position: { x: 1, y: 1 },
      size: { width: 20, height: 10 }
    }
  }
}

function makeRelativeContent(widgetIds: string[], unsupportedIds: string[] = []) {
  const widgets: Record<string, RelativeGridWidget> = {}
  for (const widgetId of widgetIds) {
    widgets[widgetId] = makeRelativeWidget(
      unsupportedIds.includes(widgetId)
        ? { type: 'not_supported', original_type: 'some_plugin' }
        : { type: WIDGET_TYPE, text: 'example' }
    )
  }
  return { layout: { type: 'relative_grid' }, widgets } as ContentRelativeGrid
}

function rectangleAt(
  layouts: ResponsiveGridWidgetLayouts,
  breakpoint: ResponsiveGridBreakpoint
): ResponsiveGridWidgetLayout {
  return layouts.layouts['default']![breakpoint]!
}

function overlaps(first: ResponsiveGridWidgetLayout, second: ResponsiveGridWidgetLayout): boolean {
  return (
    first.position.x < second.position.x + second.size.columns &&
    second.position.x < first.position.x + first.size.columns &&
    first.position.y < second.position.y + second.size.rows &&
    second.position.y < first.position.y + first.size.rows
  )
}

describe('buildResponsiveWidgetLayouts', () => {
  it('should give the first widget of the reading order the placement of an empty grid', () => {
    const content = makeRelativeContent(['a', 'b', 'c'])
    const placementOnAnEmptyGrid = createWidgetLayout(
      { layout: defaultResponsiveGridLayout(), widgets: {} },
      WIDGET_TYPE,
      constants
    )

    const widgetLayouts = buildResponsiveWidgetLayouts(['b', 'a', 'c'], content, constants)

    expect(widgetLayouts['b']).toEqual(placementOnAnEmptyGrid)
  })

  it('should follow the reading order when deciding which widget comes first', () => {
    const content = makeRelativeContent(['a', 'b'])

    const forwards = buildResponsiveWidgetLayouts(['a', 'b'], content, constants)
    const backwards = buildResponsiveWidgetLayouts(['b', 'a'], content, constants)

    expect(backwards['b']).toEqual(forwards['a'])
    expect(backwards['a']).toEqual(forwards['b'])
  })

  it('should place each widget after the one before it in the reading order', () => {
    const readingOrder = ['a', 'b', 'c', 'd']
    const content = makeRelativeContent(readingOrder)

    const widgetLayouts = buildResponsiveWidgetLayouts(readingOrder, content, constants)

    for (const breakpoint of declaredBreakpoints) {
      const placements = readingOrder.map((widgetId) =>
        rectangleAt(widgetLayouts[widgetId]!, breakpoint)
      )
      for (let index = 1; index < placements.length; index++) {
        const previous = placements[index - 1]!
        const current = placements[index]!
        expect(
          current.position.y > previous.position.y ||
            (current.position.y === previous.position.y &&
              current.position.x >= previous.position.x)
        ).toBe(true)
      }
    }
  })

  it('should declare exactly the default layout with its breakpoints for every widget', () => {
    const readingOrder = ['a', 'b']
    const content = makeRelativeContent(readingOrder)

    const widgetLayouts = buildResponsiveWidgetLayouts(readingOrder, content, constants)

    for (const widgetId of readingOrder) {
      expect(widgetLayouts[widgetId]!.type).toBe('responsive_grid')
      expect(Object.keys(widgetLayouts[widgetId]!.layouts)).toEqual(['default'])
      expect(Object.keys(widgetLayouts[widgetId]!.layouts['default']!).sort()).toEqual(
        [...declaredBreakpoints].sort()
      )
    }
  })

  it('should size every widget with its type initial size for the breakpoint', () => {
    const content = makeRelativeContent(['a'])

    const widgetLayouts = buildResponsiveWidgetLayouts(['a'], content, constants)

    for (const breakpoint of declaredBreakpoints) {
      expect(rectangleAt(widgetLayouts['a']!, breakpoint).size).toEqual(
        constants.widgets[WIDGET_TYPE]!.layout.responsive[breakpoint]!.initial_size
      )
    }
  })

  it('should not let two widgets overlap at any breakpoint', () => {
    const readingOrder = ['a', 'b', 'c', 'd', 'e']
    const content = makeRelativeContent(readingOrder)

    const widgetLayouts = buildResponsiveWidgetLayouts(readingOrder, content, constants)

    for (const breakpoint of declaredBreakpoints) {
      for (const [firstIndex, firstId] of readingOrder.entries()) {
        for (const secondId of readingOrder.slice(firstIndex + 1)) {
          expect(
            overlaps(
              rectangleAt(widgetLayouts[firstId]!, breakpoint),
              rectangleAt(widgetLayouts[secondId]!, breakpoint)
            )
          ).toBe(false)
        }
      }
    }
  })

  it('should skip a widget whose content type the API cannot represent', () => {
    const contentWithUnsupported = makeRelativeContent(['a', 'skipped', 'c'], ['skipped'])
    const contentWithoutUnsupported = makeRelativeContent(['a', 'c'])

    const withUnsupported = buildResponsiveWidgetLayouts(
      ['a', 'skipped', 'c'],
      contentWithUnsupported,
      constants
    )
    const withoutUnsupported = buildResponsiveWidgetLayouts(
      ['a', 'c'],
      contentWithoutUnsupported,
      constants
    )

    expect(Object.keys(withUnsupported)).toEqual(['a', 'c'])
    expect(withUnsupported).toEqual(withoutUnsupported)
  })

  it('should reject a reading order naming a widget the content does not hold', () => {
    const content = makeRelativeContent(['a'])

    expect(() => buildResponsiveWidgetLayouts(['a', 'missing'], content, constants)).toThrow(
      "Widget with ID 'missing' does not exist"
    )
  })
})
