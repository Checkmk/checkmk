/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { MeasuredRelativeGridLayout } from '@/dashboard/components/RelativeGrid/types'
import { createWidgetLayout } from '@/dashboard/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import { defaultResponsiveGridLayout } from '@/dashboard/components/ResponsiveGrid/composables/utils'
import {
  buildMigratedWidgetLayouts,
  buildResponsiveWidgetLayouts
} from '@/dashboard/dashboardMigration'
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
          XS: { minimum_size: { columns: 4, rows: 4 }, initial_size: { columns: 4, rows: 7 } },
          S: { minimum_size: { columns: 4, rows: 4 }, initial_size: { columns: 4, rows: 7 } },
          M: { minimum_size: { columns: 4, rows: 4 }, initial_size: { columns: 6, rows: 7 } },
          L: { minimum_size: { columns: 3, rows: 4 }, initial_size: { columns: 4, rows: 7 } },
          XL: { minimum_size: { columns: 3, rows: 4 }, initial_size: { columns: 6, rows: 7 } }
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

function endColumnOf(placement: ResponsiveGridWidgetLayout): number {
  return placement.position.x + placement.size.columns
}

function endRowOf(placement: ResponsiveGridWidgetLayout): number {
  return placement.position.y + placement.size.rows
}

function overlaps(first: ResponsiveGridWidgetLayout, second: ResponsiveGridWidgetLayout): boolean {
  return (
    first.position.x < endColumnOf(second) &&
    second.position.x < endColumnOf(first) &&
    first.position.y < endRowOf(second) &&
    second.position.y < endRowOf(first)
  )
}

function columnsAt(breakpoint: ResponsiveGridBreakpoint): number {
  return constants.responsive_grid_breakpoints[breakpoint]!.columns
}

function minimumSizeAt(breakpoint: ResponsiveGridBreakpoint) {
  return constants.widgets[WIDGET_TYPE]!.layout.responsive[breakpoint]!.minimum_size
}

function layoutViolations(widgetLayouts: Record<string, ResponsiveGridWidgetLayouts>): string[] {
  return declaredBreakpoints.flatMap((breakpoint) => {
    const placements = Object.entries(widgetLayouts).map(([widgetId, layouts]) => ({
      widgetId,
      placement: rectangleAt(layouts, breakpoint)
    }))
    const minimumSize = minimumSizeAt(breakpoint)
    const outsideGrid = placements
      .filter(
        ({ placement }) =>
          placement.position.x < 0 || endColumnOf(placement) > columnsAt(breakpoint)
      )
      .map(({ widgetId }) => `${breakpoint}: ${widgetId} lies outside the grid`)
    const belowMinimum = placements
      .filter(
        ({ placement }) =>
          placement.size.columns < minimumSize.columns || placement.size.rows < minimumSize.rows
      )
      .map(({ widgetId }) => `${breakpoint}: ${widgetId} is below its minimum size`)
    const overlapping = placements.flatMap((first, index) =>
      placements
        .slice(index + 1)
        .filter((second) => overlaps(first.placement, second.placement))
        .map((second) => `${breakpoint}: ${first.widgetId} overlaps ${second.widgetId}`)
    )
    return [...outsideGrid, ...belowMinimum, ...overlapping]
  })
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

  it('should place every widget inside the grid, at its minimum size and clear of the others', () => {
    const readingOrder = ['a', 'b', 'c', 'd', 'e']
    const content = makeRelativeContent(readingOrder)

    const widgetLayouts = buildResponsiveWidgetLayouts(readingOrder, content, constants)

    expect(layoutViolations(widgetLayouts)).toEqual([])
  })

  it('should leave widgets of unsupported types out without taking up space', () => {
    const contentWithUnsupported = makeRelativeContent(['a', 'unsupported', 'c'], ['unsupported'])
    const placementWithoutUnsupported = buildResponsiveWidgetLayouts(
      ['a', 'c'],
      makeRelativeContent(['a', 'c']),
      constants
    )

    const widgetLayouts = buildResponsiveWidgetLayouts(
      ['a', 'unsupported', 'c'],
      contentWithUnsupported,
      constants
    )

    expect(widgetLayouts).toEqual(placementWithoutUnsupported)
  })
})

const XL_GRID_WIDTH_PX = 1850
const L_GRID_WIDTH_PX = 1100

interface FrameEdges {
  left: number
  right: number
  top: number
  bottom: number
}

function measuredLayout(
  gridWidth: number,
  framesByWidgetId: Record<string, FrameEdges>
): MeasuredRelativeGridLayout {
  return {
    gridWidth,
    widgetFrames: Object.fromEntries(
      Object.entries(framesByWidgetId).map(([widgetId, { left, right, top, bottom }]) => [
        widgetId,
        { position: { left, top }, dimensions: { width: right - left, height: bottom - top } }
      ])
    ),
    readingOrder: Object.keys(framesByWidgetId)
  }
}

function migrate(measurement: MeasuredRelativeGridLayout, unsupportedIds: string[] = []) {
  const content = makeRelativeContent(Object.keys(measurement.widgetFrames), unsupportedIds)
  return buildMigratedWidgetLayouts(measurement, content, constants)
}

function readingOrderPlacement(measurement: MeasuredRelativeGridLayout) {
  const content = makeRelativeContent(Object.keys(measurement.widgetFrames))
  return buildResponsiveWidgetLayouts(measurement.readingOrder, content, constants)
}

function migratedPlacements<WidgetId extends string>(
  gridWidth: number,
  framesByWidgetId: Record<WidgetId, FrameEdges>,
  breakpoint: ResponsiveGridBreakpoint
): Record<WidgetId, ResponsiveGridWidgetLayout> {
  const widgetLayouts = migrate(measuredLayout(gridWidth, framesByWidgetId))
  return Object.fromEntries(
    Object.entries(widgetLayouts).map(([widgetId, layouts]) => [
      widgetId,
      rectangleAt(layouts, breakpoint)
    ])
  ) as Record<WidgetId, ResponsiveGridWidgetLayout>
}

function rowsSplitAtDistinctPoints(rowCount: number): Record<string, FrameEdges> {
  const rowHeightPx = 300
  const firstSplitPx = 300
  const splitStepPx = 80
  const framesByWidgetId: Record<string, FrameEdges> = {}
  for (let rowIndex = 0; rowIndex < rowCount; rowIndex++) {
    const splitPx = firstSplitPx + rowIndex * splitStepPx
    const top = rowIndex * rowHeightPx
    const bottom = top + rowHeightPx
    framesByWidgetId[`row${rowIndex}Left`] = { left: 0, right: splitPx, top, bottom }
    framesByWidgetId[`row${rowIndex}Right`] = {
      left: splitPx,
      right: XL_GRID_WIDTH_PX,
      top,
      bottom
    }
  }
  return framesByWidgetId
}

const LAYOUTS_WITHOUT_ROW_MAPPING: Record<string, Record<string, FrameEdges>> = {
  'a tall widget beside a stack': {
    tall: { left: 0, right: 925, top: 0, bottom: 600 },
    stackedUpper: { left: 925, right: 1850, top: 0, bottom: 300 },
    stackedLower: { left: 925, right: 1850, top: 300, bottom: 600 }
  },
  'overlapping widgets': {
    first: { left: 0, right: 1000, top: 0, bottom: 300 },
    second: { left: 900, right: 1850, top: 0, bottom: 300 }
  },
  'a widget past the right edge': {
    inside: { left: 0, right: 1000, top: 0, bottom: 300 },
    beyond: { left: 1000, right: 2000, top: 0, bottom: 300 }
  },
  'a widget under empty columns of the row above': {
    upper: { left: 0, right: 925, top: 0, bottom: 300 },
    lower: { left: 925, right: 1850, top: 300, bottom: 600 }
  },
  'a widget too narrow for its minimum width': {
    narrow: { left: 0, right: 100, top: 0, bottom: 300 },
    wide: { left: 100, right: 1850, top: 0, bottom: 300 }
  },
  'more distinct edges than the column search covers': rowsSplitAtDistinctPoints(15)
}

const MAIN_DASHBOARD_ARRANGEMENT: Record<string, FrameEdges> = {
  hostStatistics: { left: 0, right: 300, top: 0, bottom: 180 },
  hostGraph: { left: 300, right: 1850, top: 0, bottom: 180 },
  serviceStatistics: { left: 0, right: 300, top: 180, bottom: 360 },
  serviceGraph: { left: 300, right: 1850, top: 180, bottom: 360 },
  notifications: { left: 0, right: 300, top: 360, bottom: 540 },
  problemGraph: { left: 300, right: 1850, top: 360, bottom: 540 },
  siteOverview: { left: 0, right: 930, top: 540, bottom: 960 },
  embeddedView: { left: 930, right: 1850, top: 540, bottom: 960 }
}

describe('buildMigratedWidgetLayouts', () => {
  it('should keep the measured arrangement of the widgets', () => {
    const framesByWidgetId = {
      lower: { left: 0, right: 1850, top: 300, bottom: 600 },
      right: { left: 925, right: 1850, top: 0, bottom: 300 },
      left: { left: 0, right: 925, top: 0, bottom: 300 }
    }

    const { left, right, lower } = migratedPlacements(XL_GRID_WIDTH_PX, framesByWidgetId, 'XL')

    expect(right.position).toEqual({ x: endColumnOf(left), y: left.position.y })
    expect(lower.position.y).toBe(endRowOf(left))
  })

  it('should keep edges that rows share aligned', () => {
    const framesByWidgetId = {
      wide: { left: 0, right: 420, top: 0, bottom: 300 },
      narrow: { left: 420, right: 630, top: 0, bottom: 300 },
      upperGraph: { left: 630, right: 1240, top: 0, bottom: 300 },
      upperLastGraph: { left: 1240, right: 1850, top: 0, bottom: 300 },
      firstTile: { left: 0, right: 210, top: 300, bottom: 600 },
      secondTile: { left: 210, right: 420, top: 300, bottom: 600 },
      thirdTile: { left: 420, right: 630, top: 300, bottom: 600 },
      lowerGraph: { left: 630, right: 1240, top: 300, bottom: 600 },
      lowerLastGraph: { left: 1240, right: 1850, top: 300, bottom: 600 }
    }

    const placements = migratedPlacements(XL_GRID_WIDTH_PX, framesByWidgetId, 'XL')

    expect(placements.thirdTile.position.x).toBe(placements.narrow.position.x)
    expect(placements.lowerGraph.position.x).toBe(placements.upperGraph.position.x)
    expect(placements.lowerLastGraph.position.x).toBe(placements.upperLastGraph.position.x)
  })

  it('should prefer equal columns for widgets of equal measured width', () => {
    const framesByWidgetId = {
      first: { left: 0, right: 720, top: 0, bottom: 300 },
      second: { left: 720, right: 1440, top: 0, bottom: 300 },
      rest: { left: 1440, right: 1850, top: 0, bottom: 300 }
    }

    const { first, second, rest } = migratedPlacements(XL_GRID_WIDTH_PX, framesByWidgetId, 'XL')

    expect(second.size.columns).toBe(first.size.columns)
    expect(endColumnOf(rest)).toBe(columnsAt('XL'))
  })

  it('should map the rows without the widgets of unsupported types', () => {
    const measurement = measuredLayout(XL_GRID_WIDTH_PX, {
      upper: { left: 0, right: 1850, top: 0, bottom: 300 },
      lower: { left: 0, right: 1850, top: 300, bottom: 600 },
      unsupported: { left: 0, right: 925, top: 150, bottom: 450 }
    })

    const widgetLayouts = migrate(measurement, ['unsupported'])

    expect(widgetLayouts).not.toHaveProperty('unsupported')
    expect(rectangleAt(widgetLayouts['upper']!, 'XL').size.columns).toBe(columnsAt('XL'))
  })

  it.each(Object.entries(LAYOUTS_WITHOUT_ROW_MAPPING))(
    'should fall back to the reading order placement for %s',
    (_description, framesByWidgetId) => {
      const measurement = measuredLayout(XL_GRID_WIDTH_PX, framesByWidgetId)

      const widgetLayouts = migrate(measurement)

      expect(widgetLayouts).toEqual(readingOrderPlacement(measurement))
    }
  )

  it('should keep the offset of a widget into its row at the breakpoint of the measured width', () => {
    const framesByWidgetId = { offset: { left: 550, right: 1100, top: 0, bottom: 300 } }

    const { offset } = migratedPlacements(L_GRID_WIDTH_PX, framesByWidgetId, 'L')

    expect(offset.position.x).toBeGreaterThan(0)
  })

  it('should drop the empty columns of a row at breakpoints narrower than the measured one', () => {
    const framesByWidgetId = { offset: { left: 550, right: 1100, top: 0, bottom: 300 } }

    const { offset } = migratedPlacements(L_GRID_WIDTH_PX, framesByWidgetId, 'M')

    expect(offset.position.x).toBe(0)
    expect(offset.size.columns).toBe(columnsAt('M'))
  })

  it('should derive breakpoints wider than the measured one from the measured columns', () => {
    const framesByWidgetId = {
      left: { left: 0, right: 550, top: 0, bottom: 300 },
      right: { left: 550, right: 1100, top: 0, bottom: 300 }
    }

    const { left, right } = migratedPlacements(L_GRID_WIDTH_PX, framesByWidgetId, 'XL')

    expect(right.position.x).toBe(endColumnOf(left))
    expect(endColumnOf(right)).toBe(columnsAt('XL'))
  })

  it('should wrap a row whose widgets would fall below their minimum width', () => {
    const framesByWidgetId = {
      third: { left: 1230, right: 1850, top: 0, bottom: 300 },
      second: { left: 620, right: 1230, top: 0, bottom: 300 },
      first: { left: 0, right: 620, top: 0, bottom: 300 }
    }

    const { first, second, third } = migratedPlacements(XL_GRID_WIDTH_PX, framesByWidgetId, 'S')

    expect(second.position.y).toBe(first.position.y)
    expect(third.position.y).toBe(endRowOf(first))
  })

  it('should raise a row shorter than the minimum height to the minimum', () => {
    const framesByWidgetId = { short: { left: 0, right: 1850, top: 0, bottom: 50 } }

    const { short } = migratedPlacements(XL_GRID_WIDTH_PX, framesByWidgetId, 'XL')

    expect(short.size.rows).toBe(minimumSizeAt('XL').rows)
  })

  it('should treat edges within one raster cell as aligned', () => {
    const framesByWidgetId = {
      right: { left: 925, right: 1850, top: 0, bottom: 290 },
      left: { left: 0, right: 925, top: 0, bottom: 300 }
    }

    const { left, right } = migratedPlacements(XL_GRID_WIDTH_PX, framesByWidgetId, 'XL')

    expect(right.position).toEqual({ x: endColumnOf(left), y: left.position.y })
  })

  it('should place every widget inside the grid, at its minimum size and clear of the others', () => {
    const measurement = measuredLayout(XL_GRID_WIDTH_PX, MAIN_DASHBOARD_ARRANGEMENT)

    const widgetLayouts = migrate(measurement)

    expect(widgetLayouts).not.toEqual(readingOrderPlacement(measurement))
    expect(layoutViolations(widgetLayouts)).toEqual([])
  })
})
