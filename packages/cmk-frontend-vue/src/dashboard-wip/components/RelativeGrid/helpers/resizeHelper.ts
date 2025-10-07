/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ANCHOR_POSITION,
  type AbsoluteDimensions,
  type AbsoluteLayout,
  GRID_SIZE,
  type Position
} from '../types.ts'
import { alignToGrid, convertAbsoluteToRelativePosition } from '../utils.ts'

export type ResizeDirection =
  | 'left'
  | 'right'
  | 'top'
  | 'bottom'
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'

export interface ResizeState {
  widgetId: string
  direction: ResizeDirection
  startX: number
  startY: number
  initialLeft: number
  initialTop: number
  initialWidth: number
  initialHeight: number
  pointerId: number
  layoutAnchorPosition: ANCHOR_POSITION
  dashboardDimensions: AbsoluteDimensions
}

export interface ResizeDimensions {
  left: number
  top: number
  width: number
  height: number
}

/**
 * Creates a resize helper for handling dashlet resize functionality.
 * Uses closure to manage resize state without classes or reactive dependencies.
 */
export function createResizeHelper(
  layoutMinSize: [number, number],
  onResizeUpdate: (
    widgetId: string,
    newPosition: Position,
    newDimensions: AbsoluteDimensions
  ) => void
) {
  let resizeState: ResizeState | null = null
  let boundPointerMove: ((event: PointerEvent) => void) | null = null
  let boundPointerUp: ((event: PointerEvent) => void) | null = null

  const getCursorForDirection = (direction: ResizeDirection): string => {
    const cursors: Record<ResizeDirection, string> = {
      left: 'w-resize',
      right: 'e-resize',
      top: 'n-resize',
      bottom: 's-resize',
      'top-left': 'nw-resize',
      'top-right': 'ne-resize',
      'bottom-left': 'sw-resize',
      'bottom-right': 'se-resize'
    }
    return cursors[direction] || 'default'
  }

  const calculateNewDimensions = (
    state: ResizeState,
    deltaX: number,
    deltaY: number
  ): ResizeDimensions => {
    const { direction, initialLeft, initialTop, initialWidth, initialHeight } = state

    let newLeft = initialLeft
    let newTop = initialTop
    let newWidth = initialWidth
    let newHeight = initialHeight

    switch (direction) {
      case 'left':
        newLeft = initialLeft + deltaX
        newWidth = initialWidth - deltaX
        break
      case 'right':
        newWidth = initialWidth + deltaX
        break
      case 'top':
        newTop = initialTop + deltaY
        newHeight = initialHeight - deltaY
        break
      case 'bottom':
        newHeight = initialHeight + deltaY
        break
      case 'top-left':
        newLeft = initialLeft + deltaX
        newTop = initialTop + deltaY
        newWidth = initialWidth - deltaX
        newHeight = initialHeight - deltaY
        break
      case 'top-right':
        newTop = initialTop + deltaY
        newWidth = initialWidth + deltaX
        newHeight = initialHeight - deltaY
        break
      case 'bottom-left':
        newLeft = initialLeft + deltaX
        newWidth = initialWidth - deltaX
        newHeight = initialHeight + deltaY
        break
      case 'bottom-right':
        newWidth = initialWidth + deltaX
        newHeight = initialHeight + deltaY
        break
    }

    return { left: newLeft, top: newTop, width: newWidth, height: newHeight }
  }

  const applyConstraints = (
    dimensions: ResizeDimensions,
    dashboardDimensions: AbsoluteDimensions
  ): ResizeDimensions => {
    const minWidth = layoutMinSize[0] * GRID_SIZE
    const minHeight = layoutMinSize[1] * GRID_SIZE
    const dashboardWidth = dashboardDimensions.width
    const dashboardHeight = dashboardDimensions.height

    const constrained = { ...dimensions }

    // Ensure minimum size
    constrained.width = Math.max(constrained.width, minWidth)
    constrained.height = Math.max(constrained.height, minHeight)

    // Ensure doesn't exceed dashboard boundaries
    constrained.left = Math.max(0, Math.min(constrained.left, dashboardWidth - constrained.width))
    constrained.top = Math.max(0, Math.min(constrained.top, dashboardHeight - constrained.height))

    // Ensure right edge doesn't exceed boundary
    if (constrained.left + constrained.width > dashboardWidth) {
      constrained.width = dashboardWidth - constrained.left
    }

    // Ensure bottom edge doesn't exceed boundary
    if (constrained.top + constrained.height > dashboardHeight) {
      constrained.height = dashboardHeight - constrained.top
    }

    return constrained
  }

  /**
   * Handle pointer move events during resize
   */
  const handlePointerMove = (event: PointerEvent) => {
    if (!resizeState) {
      return
    }

    const state = resizeState

    const deltaX = event.clientX - state.startX
    const deltaY = event.clientY - state.startY

    const alignedDeltaX = alignToGrid(deltaX)
    const alignedDeltaY = alignToGrid(deltaY)

    const newDimensions = calculateNewDimensions(state, alignedDeltaX, alignedDeltaY)

    // TODO: minimum size handling
    const _constrainedDimensions = applyConstraints(newDimensions, state.dashboardDimensions)
    console.debug('Constrained dimensions', _constrainedDimensions)

    // Convert pixel position to normalized position using anchor logic
    const normalizedPosition = convertAbsoluteToRelativePosition(
      { x: newDimensions.left, y: newDimensions.top },
      { width: newDimensions.width, height: newDimensions.height },
      state.layoutAnchorPosition,
      state.dashboardDimensions
    )

    // Call callback to update resize
    onResizeUpdate(
      state.widgetId,
      { x: normalizedPosition.x, y: normalizedPosition.y },
      {
        width: alignToGrid(newDimensions.width) / GRID_SIZE,
        height: alignToGrid(newDimensions.height) / GRID_SIZE
      }
    )
  }

  /**
   * Handle pointer up/cancel events
   */
  const handlePointerUp = (event: PointerEvent) => {
    if (!resizeState) {
      return
    }

    const target = event.target as HTMLElement
    const state = resizeState

    // Clean up event listeners
    if (boundPointerMove) {
      target.removeEventListener('pointermove', boundPointerMove)
    }
    if (boundPointerUp) {
      target.removeEventListener('pointerup', boundPointerUp)
    }
    if (boundPointerUp) {
      target.removeEventListener('pointercancel', boundPointerUp)
    }

    target.releasePointerCapture(state.pointerId)
    target.style.cursor = ''
    target.style.userSelect = ''

    resizeState = null
    boundPointerMove = null
    boundPointerUp = null

    event.preventDefault()
  }

  /**
   * Start resizing a dashlet
   */
  const handleResize = (
    event: PointerEvent,
    widgetId: string,
    direction: ResizeDirection,
    anchorPosition: ANCHOR_POSITION,
    currentPixelLayout: AbsoluteLayout,
    dashboardDimensions: AbsoluteDimensions
  ) => {
    const target = event.target as HTMLElement
    target.setPointerCapture(event.pointerId)

    const currentLayout = currentPixelLayout.frame

    resizeState = {
      widgetId,
      direction,
      startX: event.clientX,
      startY: event.clientY,
      initialLeft: currentLayout.position.left,
      initialTop: currentLayout.position.top,
      initialWidth: currentLayout.dimensions.width,
      initialHeight: currentLayout.dimensions.height,
      pointerId: event.pointerId,
      layoutAnchorPosition: anchorPosition,
      dashboardDimensions: dashboardDimensions
    }

    // Create bound methods with context
    boundPointerMove = (event: PointerEvent) => handlePointerMove(event)
    boundPointerUp = (event: PointerEvent) => handlePointerUp(event)

    // Add event listeners to the captured element
    target.addEventListener('pointermove', boundPointerMove)
    target.addEventListener('pointerup', boundPointerUp)
    target.addEventListener('pointercancel', boundPointerUp)

    target.style.cursor = getCursorForDirection(direction)
    target.style.userSelect = 'none'

    event.preventDefault()
  }

  return {
    handleResize
  }
}
