/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ModelRef, computed, reactive, watch } from 'vue'

import type { ContentRelativeGrid } from '@/dashboard-wip/types/dashboard.ts'
import type { RelativeGridWidget, WidgetSizeValue } from '@/dashboard-wip/types/widget.ts'

import {
  ANCHOR_POSITION,
  type AbsoluteLayout,
  type AbsoluteWidgetLayout,
  type DimensionModes,
  type Dimensions,
  GRID_SIZE,
  GROW,
  MAX,
  type Position,
  SIZING_MODE
} from '../types.ts'
import { calculateAbsoluteLayouts, convertAbsoluteToRelativePosition } from '../utils.ts'

const widgetHasTitle = (widget: RelativeGridWidget): boolean => {
  return (
    widget.general_settings.title?.render_mode === 'with_background' ||
    widget.general_settings.title?.render_mode === 'without_background'
  )
}

const legacySizeValue = (value: WidgetSizeValue): number => {
  if (typeof value === 'number') {
    return value
  }
  if (value === 'auto') {
    return 0
  }
  if (value === 'max') {
    return -1
  }
  throw new Error(`Unsupported size value: ${value}`)
}

export function determineSizingMode(size: number): SIZING_MODE {
  if (size === MAX) {
    return SIZING_MODE.MAX
  } else if (size === GROW) {
    return SIZING_MODE.GROW
  } else {
    return SIZING_MODE.MANUAL
  }
}

export function useRelativeGridLayout(
  relativeGridContent: ModelRef<ContentRelativeGrid>,
  widgetMinSize: [number, number]
) {
  const zIndexes = reactive<Record<string, number>>({})
  const dashboardState = reactive({
    dimensions: { width: 0, height: 0 },
    position: { x: 0, y: 0 }
  })

  const absoluteWidgetLayouts = computed(() => {
    const record: Record<string, AbsoluteWidgetLayout> = {}
    const widgets = relativeGridContent.value.widgets
    if (!widgets) {
      return record
    }

    const widgetRelativeLayouts = Object.values(widgets).map((widget) => ({
      position: {
        x: widget.layout.position.x,
        y: widget.layout.position.y
      },
      dimensions: {
        width: legacySizeValue(widget.layout.size.width),
        height: legacySizeValue(widget.layout.size.height)
      }
    }))

    const absoluteLayoutsArray = calculateAbsoluteLayouts(
      widgetRelativeLayouts,
      dashboardState.dimensions,
      widgetMinSize,
      Object.values(widgets).map((widget) => ({ hasTitle: widgetHasTitle(widget) }))
    )

    Object.keys(widgets).forEach((id, index) => {
      const widget = widgets[id]!
      record[id] = {
        layout: absoluteLayoutsArray[index]!,
        anchorPosition: ANCHOR_POSITION.determine(widget.layout.position),
        dimensionModes: {
          width: determineSizingMode(legacySizeValue(widget.layout.size.width)),
          height: determineSizingMode(legacySizeValue(widget.layout.size.height))
        }
      }
    })

    return record
  })

  watch(
    () => relativeGridContent.value.widgets,
    (newWidgets) => {
      const widgetIds = Object.keys(newWidgets)
      widgetIds.forEach((id) => {
        if (zIndexes[id] === undefined) {
          zIndexes[id] = 1
        }
      })

      // cleanup removed widgets
      Object.keys(zIndexes).forEach((id) => {
        if (!newWidgets[id]) {
          delete zIndexes[id]
        }
      })
    },
    { immediate: true, deep: true }
  )

  const bringToFront = (widgetId: string) => {
    if (!zIndexes[widgetId]) {
      throw new Error(`Widget with ID '${widgetId}' does not exist`)
    }

    // Reset all z-indices to default
    Object.keys(zIndexes).forEach((id) => {
      zIndexes[id] = 1
    })

    // Bring the specified dashlet to front
    zIndexes[widgetId] = 80
  }

  const getDimensionModes = (widgetId: string): DimensionModes => {
    return getWidgetAbsoluteLayout(widgetId).dimensionModes
  }

  const getWidgetAbsoluteLayout = (widgetId: string): AbsoluteWidgetLayout => {
    const absoluteLayout = absoluteWidgetLayouts.value[widgetId]
    if (!absoluteLayout) {
      throw new Error(`Widget with ID '${widgetId}' does not exist`)
    }
    return absoluteLayout
  }

  const getAbsoluteLayout = (widgetId: string): AbsoluteLayout => {
    return getWidgetAbsoluteLayout(widgetId).layout
  }

  const getLayoutZIndex = (dashletId: string): number | null => {
    return zIndexes[dashletId] ?? null
  }

  const getAnchorPosition = (widgetId: string): ANCHOR_POSITION => {
    return absoluteWidgetLayouts.value[widgetId]!.anchorPosition
  }

  const updateDashboardLayout = (
    dimensions: { width: number; height: number },
    position: Position
  ): void => {
    dashboardState.position = { ...position }
    dashboardState.dimensions = { ...dimensions }
  }

  const updateLayoutPosition = (widgetId: string, position: Position) => {
    relativeGridContent.value.widgets[widgetId]!.layout.position = { ...position }
  }

  const updateLayoutDimensions = (widgetId: string, dimensions: Dimensions) => {
    const relativeSize = relativeGridContent.value.widgets[widgetId]!.layout.size
    const dimensionsToUpdate = { ...relativeSize }
    if (relativeSize.width !== 'max' && relativeSize.width !== 'auto') {
      dimensionsToUpdate.width = dimensions.width
    }
    if (relativeSize.height !== 'max' && relativeSize.height !== 'auto') {
      dimensionsToUpdate.height = dimensions.height
    }

    relativeGridContent.value.widgets[widgetId]!.layout.size = dimensionsToUpdate
  }

  const updateSizePosition = (
    widgetId: string,
    size: WidgetSizeValue,
    dimension: 'width' | 'height'
  ) => {
    relativeGridContent.value.widgets[widgetId]!.layout.size = {
      ...relativeGridContent.value.widgets[widgetId]!.layout.size,
      [dimension]: size
    }
  }

  const selectAnchor = (widgetId: string, newAnchorPosition: ANCHOR_POSITION) => {
    const absoluteLayout = absoluteWidgetLayouts.value[widgetId]!
    if (absoluteLayout.anchorPosition === newAnchorPosition) {
      // no change, nothing to do
      return
    }

    const absolutePosition = absoluteLayout.layout.frame.position
    const newPosition = convertAbsoluteToRelativePosition(
      { x: absolutePosition.left, y: absolutePosition.top },
      absoluteLayout.layout.frame.dimensions,
      newAnchorPosition,
      dashboardState.dimensions
    )
    updateLayoutPosition(widgetId, newPosition)
  }

  const toggleSizing = (widgetId: string, dimension: 'width' | 'height') => {
    const currentMode = absoluteWidgetLayouts.value[widgetId]!.dimensionModes[dimension]

    let newMode: SIZING_MODE
    switch (currentMode) {
      case SIZING_MODE.MANUAL:
        newMode = SIZING_MODE.GROW
        break
      case SIZING_MODE.GROW:
        newMode = SIZING_MODE.MAX
        break
      case SIZING_MODE.MAX:
        newMode = SIZING_MODE.MANUAL
        break
      default:
        throw new Error(`Unsupported sizing mode: ${currentMode}`)
    }

    let sizeValue: WidgetSizeValue
    switch (newMode) {
      case SIZING_MODE.MANUAL:
        sizeValue =
          absoluteWidgetLayouts.value[widgetId]!.layout.frame.dimensions[dimension] / GRID_SIZE
        break
      case SIZING_MODE.GROW:
        sizeValue = 'auto'
        break
      case SIZING_MODE.MAX:
        sizeValue = 'max'
        break
      default:
        throw new Error(`Unsupported sizing mode: ${newMode}`)
    }

    updateSizePosition(widgetId, sizeValue, dimension)
    bringToFront(widgetId)
  }

  return {
    dashboardState,
    getAbsoluteLayout,
    getLayoutZIndex,
    getAnchorPosition,
    getDimensionModes,

    bringToFront,
    updateDashboardLayout,
    updateLayoutPosition,
    updateLayoutDimensions,

    toggleSizing,
    selectAnchor
  }
}
