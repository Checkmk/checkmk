/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ModelRef, computed, readonly, ref } from 'vue'

import type {
  ContentResponsiveGrid,
  ResponsiveGridBreakpoint
} from '@/dashboard-wip/types/dashboard'
import type {
  ResponsiveGridWidget,
  ResponsiveGridWidgetLayout,
  ResponsiveGridWidgetLayouts
} from '@/dashboard-wip/types/widget'

import type {
  ResponsiveGridConfiguredInternalLayouts,
  ResponsiveGridInternalArrangement,
  ResponsiveGridInternalArrangementElement,
  ResponsiveGridInternalBreakpoint,
  ResponsiveGridInternalLayout
} from '../types'
import { breakpointFromInternal, breakpointToInternal, typedEntries } from './utils'

// we define this here, because the openapi schema doesn't include the breakpoint key type
type WidgetLayoutBreakpoints = Partial<Record<ResponsiveGridBreakpoint, ResponsiveGridWidgetLayout>>

function getMinimumSize(
  // @ts-expect-error: TODO: implement different minimum sizes based on widget content type
  widgetContentType: string,
  breakpoint: ResponsiveGridBreakpoint
): { columns: number; rows: number } {
  switch (breakpoint) {
    case 'XS':
      return {
        columns: 4,
        rows: 8
      }
    case 'S':
      return {
        columns: 4,
        rows: 8
      }
    case 'M':
      return {
        columns: 4,
        rows: 8
      }
    case 'L':
      return {
        columns: 3,
        rows: 8
      }
    case 'XL':
      return {
        columns: 3,
        rows: 8
      }
  }
}

function arrangementElementFromWidget(
  breakpoint: ResponsiveGridBreakpoint,
  widgetId: string,
  widgetContentType: string,
  sizeAndPos: ResponsiveGridWidgetLayout
): ResponsiveGridInternalArrangementElement {
  const minimumSize = getMinimumSize(widgetContentType, breakpoint)
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
  breakpoints: WidgetLayoutBreakpoints
): ResponsiveGridInternalLayout {
  const layout: ResponsiveGridInternalLayout = {}
  for (const [breakpoint, sizeAndPos] of typedEntries(breakpoints)) {
    layout[breakpointToInternal[breakpoint]] = [
      arrangementElementFromWidget(breakpoint, widgetId, widgetContentType, sizeAndPos)
    ]
  }
  return layout
}

function findPositionForWidget(
  arrangement: ResponsiveGridInternalArrangement,
  columns: number,
  _rows: number
): { x: number; y: number } {
  // place element in the bottom left corner
  let y = 0
  for (const element of arrangement) {
    if (element.x >= columns) {
      continue // irrelevant to us
    }
    y = Math.max(y, element.y + element.h)
  }
  return { x: 0, y }
}

function layoutsFromWidget(
  widgetId: string,
  widget: ResponsiveGridWidget
): ResponsiveGridConfiguredInternalLayouts {
  const layoutSpec = widget.layout.layouts
  const layouts: ResponsiveGridConfiguredInternalLayouts = { default: {} }
  for (const [layoutName, breakpoints] of Object.entries(layoutSpec)) {
    layouts[layoutName] = layoutFromWidget(widgetId, widget.content.type, breakpoints)
  }
  return layouts
}

function computeConfiguredInternalLayouts(
  responsiveGridContent: ContentResponsiveGrid
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
    for (const [layoutName, layoutData] of Object.entries(layoutsFromWidget(widgetId, widget))) {
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
  const configuredLayouts = computeConfiguredInternalLayouts(responsiveGridContent)
  const layoutData: ResponsiveGridWidgetLayouts['layouts'] = {}
  for (const [layoutName, gridLayouts] of Object.entries(configuredLayouts)) {
    layoutData[layoutName] = {}
    for (const [breakpoint, elements] of typedEntries(gridLayouts)) {
      const { columns, rows } = getMinimumSize(
        widgetContentType,
        breakpointFromInternal[breakpoint]
      )
      const position = findPositionForWidget(elements, columns, rows)
      layoutData[layoutName]![breakpoint] = {
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

export function useResponsiveGridLayout(responsiveGridContent: ModelRef<ContentResponsiveGrid>) {
  const layouts = computed<ResponsiveGridConfiguredInternalLayouts>(() =>
    computeConfiguredInternalLayouts(responsiveGridContent.value)
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

        const position = findPositionForWidget(arrangement, element.w, element.h)
        layoutData[layoutName]![breakpoint] = {
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
