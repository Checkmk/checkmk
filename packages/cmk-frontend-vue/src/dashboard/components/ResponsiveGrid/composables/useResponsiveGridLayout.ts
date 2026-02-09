/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ModelRef, computed, readonly, ref } from 'vue'

import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type {
  ContentResponsiveGrid,
  DashboardConstants,
  ResponsiveGridBreakpoint
} from '@/dashboard/types/dashboard'
import type {
  ResponsiveGridWidget,
  ResponsiveGridWidgetLayout,
  ResponsiveGridWidgetLayouts
} from '@/dashboard/types/widget'

import type {
  ResponsiveGridConfiguredInternalLayouts,
  ResponsiveGridInternalArrangement,
  ResponsiveGridInternalArrangementElement,
  ResponsiveGridInternalBreakpoint,
  ResponsiveGridInternalLayout
} from '../types'
import {
  type InternalBreakpointConfig,
  computeColumnsPerBreakpoint
} from './useInternalBreakpointConfig'
import { breakpointFromInternal, breakpointToInternal, typedEntries } from './utils'

// we define this here, because the openapi schema doesn't include the breakpoint key type
type WidgetLayoutBreakpoints = Partial<Record<ResponsiveGridBreakpoint, ResponsiveGridWidgetLayout>>

function getMinimumSize(
  widgetContentType: string,
  breakpoint: ResponsiveGridBreakpoint,
  widgetConstraints: DashboardConstants['widgets']
): { columns: number; rows: number } {
  return (
    widgetConstraints[widgetContentType]?.layout.responsive[breakpoint]?.minimum_size ?? {
      columns: breakpoint === 'L' || breakpoint === 'XL' ? 3 : 4,
      rows: 8
    }
  )
}

function getDefaultSize(
  widgetContentType: string,
  breakpoint: ResponsiveGridBreakpoint,
  widgetConstraints: DashboardConstants['widgets']
): { columns: number; rows: number } {
  return (
    widgetConstraints[widgetContentType]?.layout.responsive[breakpoint]?.initial_size ??
    getMinimumSize(widgetContentType, breakpoint, widgetConstraints)
  )
}

function arrangementElementFromWidget(
  breakpoint: ResponsiveGridBreakpoint,
  widgetId: string,
  widgetContentType: string,
  sizeAndPos: ResponsiveGridWidgetLayout,
  widgetConstraints: DashboardConstants['widgets']
): ResponsiveGridInternalArrangementElement {
  const minimumSize = getMinimumSize(widgetContentType, breakpoint, widgetConstraints)
  return {
    i: widgetId,
    x: sizeAndPos.position.x,
    y: sizeAndPos.position.y,
    w: sizeAndPos.size.columns,
    h: sizeAndPos.size.rows,
    minW: minimumSize.columns,
    minH: minimumSize.rows
  } as ResponsiveGridInternalArrangementElement
}

function layoutFromWidget(
  widgetId: string,
  widgetContentType: string,
  breakpoints: WidgetLayoutBreakpoints,
  widgetConstraints: DashboardConstants['widgets']
): ResponsiveGridInternalLayout {
  const layout: ResponsiveGridInternalLayout = {}
  for (const [breakpoint, sizeAndPos] of typedEntries(breakpoints)) {
    layout[breakpointToInternal[breakpoint]] = [
      arrangementElementFromWidget(
        breakpoint,
        widgetId,
        widgetContentType,
        sizeAndPos,
        widgetConstraints
      )
    ]
  }
  return layout
}

function findPositionForWidget(
  arrangement: ResponsiveGridInternalArrangement,
  arrangementMaxColumns: number,
  columns: number,
  rows: number
): { x: number; y: number } {
  // place element in the highest possible row, left aligned
  if (arrangement.length === 0) {
    return { x: 0, y: 0 }
  }
  for (let y = 0; ; y++) {
    for (let x = 0; x <= arrangementMaxColumns - columns; x++) {
      // check if it fits at (x, y)
      let overlaps = false
      for (const element of arrangement) {
        const overlapX = x + columns > element.x && x < element.x + element.w
        const overlapY = y + rows > element.y && y < element.y + element.h
        if (overlapX && overlapY) {
          overlaps = true
          break
        }
      }
      if (!overlaps) {
        return { x, y }
      }
    }
  }
}

function layoutsFromWidget(
  widgetId: string,
  widget: ResponsiveGridWidget,
  widgetConstraints: DashboardConstants['widgets']
): ResponsiveGridConfiguredInternalLayouts {
  const layoutSpec = widget.layout.layouts
  const layouts: ResponsiveGridConfiguredInternalLayouts = { default: {} }
  for (const [layoutName, breakpoints] of Object.entries(layoutSpec)) {
    layouts[layoutName] = layoutFromWidget(
      widgetId,
      widget.content.type,
      breakpoints,
      widgetConstraints
    )
  }
  return layouts
}

function computeConfiguredInternalLayouts(
  responsiveGridContent: ContentResponsiveGrid,
  widgetConstraints: DashboardConstants['widgets']
): ResponsiveGridConfiguredInternalLayouts {
  const newLayouts: ResponsiveGridConfiguredInternalLayouts = {
    default: {}
  }
  for (const [layoutName, layoutSettings] of Object.entries(responsiveGridContent.layout.layouts)) {
    newLayouts[layoutName] = {}
    for (const breakpoint of layoutSettings.breakpoints) {
      newLayouts[layoutName]![breakpointToInternal[breakpoint]] = []
    }
  }
  for (const [widgetId, widget] of Object.entries(responsiveGridContent.widgets)) {
    for (const [layoutName, layoutData] of Object.entries(
      layoutsFromWidget(widgetId, widget, widgetConstraints)
    )) {
      for (const [breakpoint, elements] of typedEntries(layoutData)) {
        newLayouts[layoutName]![breakpoint]!.push(...elements)
      }
    }
  }
  return newLayouts
}

export function createWidgetLayout(
  responsiveGridContent: ContentResponsiveGrid,
  widgetContentType: string
): ResponsiveGridWidgetLayouts {
  const constants = useInjectDashboardConstants()
  const configuredLayouts = computeConfiguredInternalLayouts(
    responsiveGridContent,
    constants.widgets
  )
  const columnsPerBreakpoint = computeColumnsPerBreakpoint(constants.responsive_grid_breakpoints)
  const layoutData: ResponsiveGridWidgetLayouts['layouts'] = {}
  for (const [layoutName, gridLayouts] of Object.entries(configuredLayouts)) {
    layoutData[layoutName] = {}
    for (const [breakpoint, elements] of typedEntries(gridLayouts)) {
      const externalBreakpoint = breakpointFromInternal[breakpoint]
      const { columns, rows } = getDefaultSize(
        widgetContentType,
        externalBreakpoint,
        constants.widgets
      )
      const position = findPositionForWidget(
        elements,
        columnsPerBreakpoint[breakpoint],
        columns,
        rows
      )
      layoutData[layoutName]![externalBreakpoint] = {
        position,
        size: {
          columns,
          rows
        }
      }
    }
  }
  return {
    type: 'responsive_grid',
    layouts: layoutData
  } as ResponsiveGridWidgetLayouts
}

export function useResponsiveGridLayout(
  breakpointConfig: InternalBreakpointConfig,
  responsiveGridContent: ModelRef<ContentResponsiveGrid>,
  widgetConstraints: DashboardConstants['widgets']
) {
  const layouts = computed<ResponsiveGridConfiguredInternalLayouts>(() =>
    computeConfiguredInternalLayouts(responsiveGridContent.value, widgetConstraints)
  )

  const availableLayouts = computed<string[]>(() => Object.keys(layouts.value))
  const selectedLayoutName = ref<keyof ResponsiveGridConfiguredInternalLayouts>('default')
  const selectedLayout = computed<ResponsiveGridInternalLayout>(
    () => layouts.value[selectedLayoutName.value]!
  )

  function selectLayout(name: keyof ResponsiveGridConfiguredInternalLayouts) {
    if (name in layouts.value) {
      selectedLayoutName.value = name
    } else {
      throw new Error(`Layout ${name} does not exist`)
    }
  }

  function cloneWidgetLayout(widgetId: string): ResponsiveGridWidgetLayouts | null {
    // copy the size of the widget in all layouts, but find a new position for it
    // return null if the widget does not exist in all layouts
    const layoutData: ResponsiveGridWidgetLayouts['layouts'] = {}
    for (const [layoutName, layout] of Object.entries(layouts.value)) {
      layoutData[layoutName] = {}
      for (const [breakpoint, arrangement] of typedEntries(layout)) {
        const element = arrangement.find((e) => e.i === widgetId)
        if (!element) {
          return null // widget not found in this layout
        }

        const position = findPositionForWidget(
          arrangement,
          breakpointConfig.value.columns[breakpoint],
          element.w,
          element.h
        )
        layoutData[layoutName]![breakpointFromInternal[breakpoint]] = {
          position,
          size: {
            columns: element.w,
            rows: element.h
          }
        }
      }
    }
    return {
      type: 'responsive_grid',
      layouts: layoutData
    } as ResponsiveGridWidgetLayouts
  }

  function updateSelectedLayout(
    breakpoint: ResponsiveGridInternalBreakpoint,
    newArrangement: ResponsiveGridInternalArrangement
  ): void {
    newArrangement.forEach((element) => {
      responsiveGridContent.value.widgets[element.i]!.layout.layouts[selectedLayoutName.value]![
        breakpointFromInternal[breakpoint]
      ] = {
        position: {
          x: element.x,
          y: element.y
        },
        size: {
          columns: element.w,
          rows: element.h
        }
      }
    })
  }

  return {
    layouts,
    availableLayouts,
    selectedLayoutName: readonly(selectedLayoutName),
    selectedLayout,

    selectLayout,
    updateSelectedLayout,
    cloneWidgetLayout
  }
}
