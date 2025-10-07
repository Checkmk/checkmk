/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  ANCHOR_POSITION,
  type AbsoluteLayout,
  type DimensionModes,
  GRID_SIZE,
  type Position,
  SIZING_MODE
} from '../types.ts'
import { alignToGrid, convertAbsoluteToRelativePosition } from '../utils.ts'

export interface DragState {
  dashletId: string
  initialMouseDashboardX: number
  initialMouseDashboardY: number
  initialDashletPixelX: number
  initialDashletPixelY: number
  dashletEffectiveWidth: number
  dashletEffectiveHeight: number
  layoutAnchorPosition: ANCHOR_POSITION
  pointerId: number
  capturedElement: HTMLElement
}

/**
 * Creates a drag helper for handling dashlet drag functionality.
 * Uses closure to manage drag state without classes or reactive dependencies.
 */
export function createDragHelper(
  dashboardPosition: Position,
  layoutMinSize: [number, number],
  onPositionUpdate: (dashletId: string, newPosition: Position) => void
) {
  let dragState: DragState | null = null
  let boundPointerMove: ((event: PointerEvent) => void) | null = null
  let boundPointerUp: ((event: PointerEvent) => void) | null = null

  /**
   * Handle pointer move events during drag
   */
  const handlePointerMove = (event: PointerEvent) => {
    if (!dragState) {
      return
    }

    const state = dragState

    const dashboardElement = state.capturedElement.closest('.dashboard') as HTMLElement
    if (!dashboardElement) {
      return
    }

    const dashboardWidth = dashboardElement.clientWidth
    const dashboardHeight = dashboardElement.clientHeight

    const mouseDashboardX = event.clientX - dashboardPosition.x
    const mouseDashboardY = event.clientY - dashboardPosition.y

    const deltaX = alignToGrid(state.initialMouseDashboardX - mouseDashboardX)
    const deltaY = alignToGrid(state.initialMouseDashboardY - mouseDashboardY)

    let newX = state.initialDashletPixelX - deltaX
    let newY = state.initialDashletPixelY - deltaY

    // Apply boundaries
    if (newX < 0) {
      newX = 0
    } else if (newX + state.dashletEffectiveWidth > dashboardWidth) {
      newX = dashboardWidth - state.dashletEffectiveWidth
    }

    if (newY < 0) {
      newY = 0
    } else if (newY + state.dashletEffectiveHeight > dashboardHeight) {
      newY = dashboardHeight - state.dashletEffectiveHeight
    }

    const relativePosition = convertAbsoluteToRelativePosition(
      { x: newX, y: newY },
      { width: state.dashletEffectiveWidth, height: state.dashletEffectiveHeight },
      state.layoutAnchorPosition,
      { width: dashboardWidth, height: dashboardHeight }
    )

    // TODO: consider changing this to return the updated Position instead and do the update outside
    // Call callback to update position
    onPositionUpdate(state.dashletId, relativePosition)
  }

  /**
   * Handle pointer up/cancel events
   */
  const handlePointerUp = (event: PointerEvent) => {
    if (!dragState) {
      return
    }

    const state = dragState
    const target = state.capturedElement

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

    dragState = null
    boundPointerMove = null
    boundPointerUp = null

    event.preventDefault()
  }

  /**
   * Start dragging a dashlet
   */
  const handleDrag = (
    event: PointerEvent,
    dashletId: string,
    anchorPosition: ANCHOR_POSITION,
    dimensionModes: DimensionModes,
    currentPixelLayout: AbsoluteLayout
  ) => {
    const target = event.target as HTMLElement

    target.setPointerCapture(event.pointerId)

    const minWidth = layoutMinSize[0] * GRID_SIZE
    const minHeight = layoutMinSize[1] * GRID_SIZE
    const anchor = anchorPosition

    // Start with current layout dimensions and position
    let effectiveX = currentPixelLayout.frame.position.left
    let effectiveY = currentPixelLayout.frame.position.top
    let effectiveWidth = currentPixelLayout.frame.dimensions.width
    let effectiveHeight = currentPixelLayout.frame.dimensions.height

    // Apply anchor-based size reduction logic
    if (anchor === ANCHOR_POSITION.TOP_LEFT) {
      if (dimensionModes.width !== SIZING_MODE.MANUAL) {
        effectiveWidth = minWidth
      }
      if (dimensionModes.height !== SIZING_MODE.MANUAL) {
        effectiveHeight = minHeight
      }
    } else if (anchor === ANCHOR_POSITION.TOP_RIGHT) {
      if (dimensionModes.width !== SIZING_MODE.MANUAL) {
        effectiveX = effectiveX + effectiveWidth - minWidth
        effectiveWidth = minWidth
      }
      if (dimensionModes.height !== SIZING_MODE.MANUAL) {
        effectiveHeight = minHeight
      }
    } else if (anchor === ANCHOR_POSITION.BOTTOM_RIGHT) {
      if (dimensionModes.width !== SIZING_MODE.MANUAL) {
        effectiveX = effectiveX + effectiveWidth - minWidth
        effectiveWidth = minWidth
      }
      if (dimensionModes.height !== SIZING_MODE.MANUAL) {
        effectiveY = effectiveY + effectiveHeight - minHeight
        effectiveHeight = minHeight
      }
    } else if (anchor === ANCHOR_POSITION.BOTTOM_LEFT) {
      if (dimensionModes.width !== SIZING_MODE.MANUAL) {
        effectiveWidth = minWidth
      }
      if (dimensionModes.height !== SIZING_MODE.MANUAL) {
        effectiveY = effectiveY + effectiveHeight - minHeight
        effectiveHeight = minHeight
      }
    }

    dragState = {
      dashletId,
      initialMouseDashboardX: event.clientX - dashboardPosition.x,
      initialMouseDashboardY: event.clientY - dashboardPosition.y,
      initialDashletPixelX: effectiveX,
      initialDashletPixelY: effectiveY,
      dashletEffectiveWidth: effectiveWidth,
      dashletEffectiveHeight: effectiveHeight,
      layoutAnchorPosition: anchorPosition,
      pointerId: event.pointerId,
      capturedElement: target
    }

    // Create bound methods with context
    boundPointerMove = (event: PointerEvent) => handlePointerMove(event)
    boundPointerUp = (event: PointerEvent) => handlePointerUp(event)

    // Add event listeners to the captured element
    target.addEventListener('pointermove', boundPointerMove)
    target.addEventListener('pointerup', boundPointerUp)
    target.addEventListener('pointercancel', boundPointerUp)

    // Update cursor and prevent text selection
    target.style.cursor = 'grabbing'
    target.style.userSelect = 'none'

    event.preventDefault()
  }

  // Return the public interface
  return {
    handleDrag
  }
}
