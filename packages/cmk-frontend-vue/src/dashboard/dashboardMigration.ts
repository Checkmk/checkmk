/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  GRID_SIZE,
  type MeasuredRelativeGridLayout
} from '@/dashboard/components/RelativeGrid/types'
import {
  createWidgetLayout,
  getMinimumSize
} from '@/dashboard/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import {
  RESPONSIVE_GRID_MARGIN_PX,
  RESPONSIVE_GRID_ROW_HEIGHT_PX,
  defaultResponsiveGridLayout
} from '@/dashboard/components/ResponsiveGrid/composables/utils'
import type {
  ContentRelativeGrid,
  ContentResponsiveGrid,
  DashboardConstants,
  ResponsiveGridBreakpoint
} from '@/dashboard/types/dashboard'
import type {
  ResponsiveGridWidget,
  ResponsiveGridWidgetLayout,
  ResponsiveGridWidgetLayouts
} from '@/dashboard/types/widget'

export function buildReadingOrderWidgetLayouts(
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

const EDGE_ALIGNMENT_TOLERANCE_PX = GRID_SIZE
const MAX_SEARCHED_COLUMN_EDGES = 16
const GRID_ROW_PITCH_PX = RESPONSIVE_GRID_ROW_HEIGHT_PX + RESPONSIVE_GRID_MARGIN_PX

interface AlignedWidget {
  widgetId: string
  contentType: string
  left: number
  right: number
  top: number
  bottom: number
}

interface WidgetRow {
  heightPx: number
  widgetsLeftToRight: AlignedWidget[]
}

interface ColumnSpan {
  start: number
  end: number
}

interface ScoredColumnChoice {
  columnPerEdge: number[]
  splitEqualWidthGroups: number
  squaredDeviation: number
}

type BreakpointPlacements = Record<string, ResponsiveGridWidgetLayout>

export function buildMigratedWidgetLayouts(
  measurement: MeasuredRelativeGridLayout,
  relativeContent: ContentRelativeGrid,
  constants: DashboardConstants
): Record<string, ResponsiveGridWidgetLayouts> {
  return (
    buildRowWidgetLayouts(measurement, relativeContent, constants) ??
    buildReadingOrderWidgetLayouts(measurement.readingOrder, relativeContent, constants)
  )
}

function buildRowWidgetLayouts(
  measurement: MeasuredRelativeGridLayout,
  relativeContent: ContentRelativeGrid,
  constants: DashboardConstants
): Record<string, ResponsiveGridWidgetLayouts> | null {
  const widgets = alignSupportedWidgets(measurement, relativeContent)
  if (widgets === null || !fitsGridWidth(widgets, measurement.gridWidth) || hasOverlap(widgets)) {
    return null
  }
  const rows = splitIntoRows(widgets)
  if (rows === null) {
    return null
  }

  const measuredBreakpoint = breakpointForWidth(measurement.gridWidth, constants)
  const placementsByBreakpoint = new Map<ResponsiveGridBreakpoint, BreakpointPlacements>()
  for (const breakpoint of declaredBreakpoints()) {
    const placements = isNarrower(breakpoint, measuredBreakpoint, constants)
      ? wrapRows(rows, breakpoint, constants)
      : placeRowsOnMeasuredColumns(rows, measurement.gridWidth, breakpoint, constants)
    if (placements === null) {
      return null
    }
    placementsByBreakpoint.set(breakpoint, placements)
  }

  return assembleWidgetLayouts(widgets, placementsByBreakpoint)
}

function alignSupportedWidgets(
  measurement: MeasuredRelativeGridLayout,
  relativeContent: ContentRelativeGrid
): AlignedWidget[] | null {
  const measuredWidgets: AlignedWidget[] = []
  for (const [widgetId, widget] of Object.entries(relativeContent.widgets)) {
    if (widget.content.type === 'not_supported') {
      continue
    }
    const frame = measurement.widgetFrames[widgetId]
    if (frame === undefined) {
      return null
    }
    measuredWidgets.push({
      widgetId,
      contentType: widget.content.type,
      left: frame.position.left,
      right: frame.position.left + frame.dimensions.width,
      top: frame.position.top,
      bottom: frame.position.top + frame.dimensions.height
    })
  }

  const alignHorizontalEdge = edgeAligner(
    measuredWidgets.flatMap(({ left, right }) => [left, right])
  )
  const alignVerticalEdge = edgeAligner(measuredWidgets.flatMap(({ top, bottom }) => [top, bottom]))
  return measuredWidgets.map((widget) => ({
    ...widget,
    left: alignHorizontalEdge(widget.left),
    right: alignHorizontalEdge(widget.right),
    top: alignVerticalEdge(widget.top),
    bottom: alignVerticalEdge(widget.bottom)
  }))
}

function edgeAligner(edges: number[]): (edge: number) => number {
  const alignedEdges = new Map<number, number>()
  let alignedEdge: number | null = null
  for (const edge of [...new Set(edges)].sort((first, second) => first - second)) {
    if (alignedEdge === null || edge - alignedEdge > EDGE_ALIGNMENT_TOLERANCE_PX) {
      alignedEdge = edge
    }
    alignedEdges.set(edge, alignedEdge)
  }
  return (edge) => alignedEdges.get(edge)!
}

function fitsGridWidth(widgets: AlignedWidget[], gridWidth: number): boolean {
  return widgets.every((widget) => widget.left >= 0 && widget.right <= gridWidth)
}

function hasOverlap(widgets: AlignedWidget[]): boolean {
  return widgets.some((widget, index) =>
    widgets
      .slice(index + 1)
      .some(
        (other) =>
          spansOverlap(widget.left, widget.right, other.left, other.right) &&
          spansOverlap(widget.top, widget.bottom, other.top, other.bottom)
      )
  )
}

function spansOverlap(
  firstStart: number,
  firstEnd: number,
  secondStart: number,
  secondEnd: number
) {
  return firstStart < secondEnd && secondStart < firstEnd
}

function splitIntoRows(widgets: AlignedWidget[]): WidgetRow[] | null {
  const widgetsTopToBottom = [...widgets].sort(
    (first, second) => first.top - second.top || first.left - second.left
  )
  const rows: { top: number; bottom: number; widgetsLeftToRight: AlignedWidget[] }[] = []
  for (const widget of widgetsTopToBottom) {
    const currentRow = rows.at(-1)
    if (currentRow?.top === widget.top && currentRow.bottom === widget.bottom) {
      currentRow.widgetsLeftToRight.push(widget)
    } else if (currentRow === undefined || widget.top >= currentRow.bottom) {
      rows.push({ top: widget.top, bottom: widget.bottom, widgetsLeftToRight: [widget] })
    } else {
      return null
    }
  }
  return rows.map(({ top, bottom, widgetsLeftToRight }) => ({
    heightPx: bottom - top,
    widgetsLeftToRight
  }))
}

function declaredBreakpoints(): ResponsiveGridBreakpoint[] {
  const layouts = Object.values(defaultResponsiveGridLayout().layouts)
  return [...new Set(layouts.flatMap((layout) => layout.breakpoints as ResponsiveGridBreakpoint[]))]
}

function breakpointSettings(constants: DashboardConstants, breakpoint: ResponsiveGridBreakpoint) {
  const settings = constants.responsive_grid_breakpoints[breakpoint]
  if (settings === undefined) {
    throw new Error(`Breakpoint '${breakpoint}' is not configured`)
  }
  return settings
}

function breakpointForWidth(
  width: number,
  constants: DashboardConstants
): ResponsiveGridBreakpoint {
  const [narrowest, ...wider] = (
    Object.keys(constants.responsive_grid_breakpoints) as ResponsiveGridBreakpoint[]
  ).sort(
    (first, second) =>
      breakpointSettings(constants, first).min_width -
      breakpointSettings(constants, second).min_width
  )
  return wider.reduce(
    (matching, breakpoint) =>
      width > breakpointSettings(constants, breakpoint).min_width ? breakpoint : matching,
    narrowest!
  )
}

function isNarrower(
  breakpoint: ResponsiveGridBreakpoint,
  reference: ResponsiveGridBreakpoint,
  constants: DashboardConstants
): boolean {
  return (
    breakpointSettings(constants, breakpoint).min_width <
    breakpointSettings(constants, reference).min_width
  )
}

function minimumColumns(
  widget: AlignedWidget,
  breakpoint: ResponsiveGridBreakpoint,
  constants: DashboardConstants
): number {
  return getMinimumSize(widget.contentType, breakpoint, constants.widgets).columns
}

function rowHeightInGridRows(
  row: WidgetRow,
  breakpoint: ResponsiveGridBreakpoint,
  constants: DashboardConstants
): number {
  const gridRowsSpanningMeasuredHeight = Math.round(
    (row.heightPx + RESPONSIVE_GRID_MARGIN_PX) / GRID_ROW_PITCH_PX
  )
  const minimumRows = row.widgetsLeftToRight.map(
    (widget) => getMinimumSize(widget.contentType, breakpoint, constants.widgets).rows
  )
  return Math.max(gridRowsSpanningMeasuredHeight, ...minimumRows)
}

function placeRowsOnMeasuredColumns(
  rows: WidgetRow[],
  gridWidth: number,
  breakpoint: ResponsiveGridBreakpoint,
  constants: DashboardConstants
): BreakpointPlacements | null {
  const columnAt = chooseEdgeColumns(
    rows,
    gridWidth,
    breakpointSettings(constants, breakpoint).columns,
    (widget) => minimumColumns(widget, breakpoint, constants)
  )
  if (columnAt === null) {
    return null
  }

  const placements: BreakpointPlacements = {}
  let rowY = 0
  let spansOfRowAbove: ColumnSpan[] | null = null
  for (const row of rows) {
    const rowHeight = rowHeightInGridRows(row, breakpoint, constants)
    const spans = row.widgetsLeftToRight.map((widget) => ({
      start: columnAt(widget.left),
      end: columnAt(widget.right)
    }))
    if (spansOfRowAbove !== null && anySpanLiesUnderEmptyColumns(spans, spansOfRowAbove)) {
      return null
    }
    for (const [index, widget] of row.widgetsLeftToRight.entries()) {
      const span = spans[index]!
      placements[widget.widgetId] = {
        position: { x: span.start, y: rowY },
        size: { columns: span.end - span.start, rows: rowHeight }
      }
    }
    rowY += rowHeight
    spansOfRowAbove = spans
  }
  return placements
}

function anySpanLiesUnderEmptyColumns(spans: ColumnSpan[], spansOfRowAbove: ColumnSpan[]): boolean {
  return spans.some(
    (span) =>
      !spansOfRowAbove.some((above) => spansOverlap(span.start, span.end, above.start, above.end))
  )
}

function chooseEdgeColumns(
  rows: WidgetRow[],
  gridWidth: number,
  columnCount: number,
  minimumColumnsOf: (widget: AlignedWidget) => number
): ((edge: number) => number) | null {
  const widgets = rows.flatMap((row) => row.widgetsLeftToRight)
  const edges = [...new Set(widgets.flatMap((widget) => [widget.left, widget.right]))].sort(
    (first, second) => first - second
  )
  if (edges.length > MAX_SEARCHED_COLUMN_EDGES) {
    return null
  }

  const edgeIndex = new Map(edges.map((edge, index) => [edge, index]))
  const indexOf = (edge: number) => edgeIndex.get(edge)!
  const exactColumns = edges.map((edge) => (edge / gridWidth) * columnCount)
  const candidateColumns = exactColumns.map((exactColumn) =>
    [...new Set([Math.floor(exactColumn), Math.ceil(exactColumn)])].filter(
      (column) => column >= 0 && column <= columnCount
    )
  )
  const widgetsEndingAtEdge = edges.map((edge) => widgets.filter((widget) => widget.right === edge))
  const equalWidthGroups = groupByWidth(widgets).filter((group) => group.length > 1)
  const widthInColumns = (widget: AlignedWidget, columnPerEdge: number[]) =>
    columnPerEdge[indexOf(widget.right)]! - columnPerEdge[indexOf(widget.left)]!

  function* choicesMeetingMinimums(chosenColumns: number[]): Generator<number[]> {
    const edgeToChoose = chosenColumns.length
    if (edgeToChoose === edges.length) {
      yield chosenColumns
      return
    }
    for (const column of candidateColumns[edgeToChoose]!) {
      if (edgeToChoose > 0 && column < chosenColumns[edgeToChoose - 1]!) {
        continue
      }
      const extendedColumns = [...chosenColumns, column]
      const endingWidgetsMeetMinimum = widgetsEndingAtEdge[edgeToChoose]!.every(
        (widget) => widthInColumns(widget, extendedColumns) >= minimumColumnsOf(widget)
      )
      if (endingWidgetsMeetMinimum) {
        yield* choicesMeetingMinimums(extendedColumns)
      }
    }
  }

  const scoreChoice = (columnPerEdge: number[]): ScoredColumnChoice => ({
    columnPerEdge,
    splitEqualWidthGroups: equalWidthGroups.filter(
      (group) => new Set(group.map((widget) => widthInColumns(widget, columnPerEdge))).size > 1
    ).length,
    squaredDeviation: sum(
      columnPerEdge.map((column, index) => (column - exactColumns[index]!) ** 2)
    )
  })

  let preferredChoice: ScoredColumnChoice | null = null
  for (const columnPerEdge of choicesMeetingMinimums([])) {
    const choice = scoreChoice(columnPerEdge)
    if (preferredChoice === null || isPreferred(choice, preferredChoice)) {
      preferredChoice = choice
    }
  }
  if (preferredChoice === null) {
    return null
  }
  const { columnPerEdge } = preferredChoice
  return (edge) => columnPerEdge[indexOf(edge)]!
}

function groupByWidth(widgets: AlignedWidget[]): AlignedWidget[][] {
  const widgetsByWidth = new Map<number, AlignedWidget[]>()
  for (const widget of widgets) {
    const width = widget.right - widget.left
    widgetsByWidth.set(width, [...(widgetsByWidth.get(width) ?? []), widget])
  }
  return [...widgetsByWidth.values()]
}

function isPreferred(candidate: ScoredColumnChoice, current: ScoredColumnChoice): boolean {
  if (candidate.splitEqualWidthGroups !== current.splitEqualWidthGroups) {
    return candidate.splitEqualWidthGroups < current.splitEqualWidthGroups
  }
  return candidate.squaredDeviation < current.squaredDeviation
}

function wrapRows(
  rows: WidgetRow[],
  breakpoint: ResponsiveGridBreakpoint,
  constants: DashboardConstants
): BreakpointPlacements {
  const columnCount = breakpointSettings(constants, breakpoint).columns
  const placements: BreakpointPlacements = {}
  let lineY = 0
  for (const row of rows) {
    const lineHeight = rowHeightInGridRows(row, breakpoint, constants)
    const lines = wrapIntoLines(row.widgetsLeftToRight, columnCount, (widget) =>
      minimumColumns(widget, breakpoint, constants)
    )
    for (const line of lines) {
      const columnsPerWidget = shareColumns(line, columnCount)
      let lineX = 0
      for (const [index, widget] of line.entries()) {
        const columns = columnsPerWidget[index]!
        placements[widget.widgetId] = {
          position: { x: lineX, y: lineY },
          size: { columns, rows: lineHeight }
        }
        lineX += columns
      }
      lineY += lineHeight
    }
  }
  return placements
}

function wrapIntoLines(
  widgetsLeftToRight: AlignedWidget[],
  columnCount: number,
  minimumColumnsOf: (widget: AlignedWidget) => number
): AlignedWidget[][] {
  const lines: AlignedWidget[][] = []
  let currentLine: AlignedWidget[] = []
  for (const widget of widgetsLeftToRight) {
    const extendedLine = [...currentLine, widget]
    if (currentLine.length === 0 || fitsOnOneLine(extendedLine, columnCount, minimumColumnsOf)) {
      currentLine = extendedLine
    } else {
      lines.push(currentLine)
      currentLine = [widget]
    }
  }
  lines.push(currentLine)
  return lines
}

function fitsOnOneLine(
  widgets: AlignedWidget[],
  columnCount: number,
  minimumColumnsOf: (widget: AlignedWidget) => number
): boolean {
  return shareColumns(widgets, columnCount).every(
    (columns, index) => columns >= minimumColumnsOf(widgets[index]!)
  )
}

function shareColumns(widgets: AlignedWidget[], columnCount: number): number[] {
  const widths = widgets.map((widget) => widget.right - widget.left)
  const totalWidth = sum(widths)
  const exactShares = widths.map((width) => (width / totalWidth) * columnCount)
  const shares = exactShares.map((exactShare) => Math.floor(exactShare))
  const sharesByLargestRemainder = exactShares
    .map((exactShare, index) => ({ index, remainder: exactShare - shares[index]! }))
    .sort((first, second) => second.remainder - first.remainder)
  for (const { index } of sharesByLargestRemainder.slice(0, columnCount - sum(shares))) {
    shares[index] = shares[index]! + 1
  }
  return shares
}

function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0)
}

function assembleWidgetLayouts(
  widgets: AlignedWidget[],
  placementsByBreakpoint: Map<ResponsiveGridBreakpoint, BreakpointPlacements>
): Record<string, ResponsiveGridWidgetLayouts> {
  const layoutsByName = Object.entries(defaultResponsiveGridLayout().layouts)
  return Object.fromEntries(
    widgets.map(({ widgetId }) => [
      widgetId,
      {
        type: 'responsive_grid',
        layouts: Object.fromEntries(
          layoutsByName.map(([layoutName, layout]) => [
            layoutName,
            Object.fromEntries(
              (layout.breakpoints as ResponsiveGridBreakpoint[]).map((breakpoint) => [
                breakpoint,
                placementsByBreakpoint.get(breakpoint)![widgetId]!
              ])
            )
          ])
        )
      } as ResponsiveGridWidgetLayouts
    ])
  )
}
