/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Dragging a static map around when it does not fit its pane.
 *
 * That happens either because the operator zoomed in, or because the
 * NagVis-compatible renderer draws at the background's native size. Panning
 * scrolls the containing element rather than transforming the canvas, so the
 * scrollbars stay truthful about where in the map the view is.
 */
import { type Ref, ref } from 'vue'

export interface CanvasPan {
  active: Ref<boolean>
  /** Take the gesture, or leave it for the next handler. */
  tryBegin: (event: PointerEvent) => boolean
  move: (event: PointerEvent) => boolean
  end: () => boolean
}

export function useCanvasPan(source: {
  canvas: () => HTMLElement | null
  scroller: () => HTMLElement | null
  /** Whether the canvas currently overflows its pane. */
  pannable: () => boolean
}): CanvasPan {
  const active = ref(false)
  let pointerId: number | null = null
  let scroller: HTMLElement | null = null
  let fromX = 0
  let fromY = 0
  let fromScrollLeft = 0
  let fromScrollTop = 0

  function tryBegin(event: PointerEvent): boolean {
    if (!source.pannable()) {
      return false
    }
    // A press on an object is that object's, not the pane's.
    if ((event.target as HTMLElement | null)?.closest('[data-object-id]')) {
      return false
    }
    const target = source.scroller()
    if (!target) {
      return false
    }
    active.value = true
    pointerId = event.pointerId
    scroller = target
    fromX = event.clientX
    fromY = event.clientY
    fromScrollLeft = target.scrollLeft
    fromScrollTop = target.scrollTop
    source.canvas()?.setPointerCapture(event.pointerId)
    return true
  }

  function move(event: PointerEvent): boolean {
    if (!active.value || !scroller) {
      return false
    }
    scroller.scrollLeft = fromScrollLeft - (event.clientX - fromX)
    scroller.scrollTop = fromScrollTop - (event.clientY - fromY)
    return true
  }

  function end(): boolean {
    if (!active.value) {
      return false
    }
    active.value = false
    if (pointerId !== null) {
      try {
        source.canvas()?.releasePointerCapture(pointerId)
      } catch {
        // The pointer may already have been released.
      }
    }
    pointerId = null
    scroller = null
    return true
  }

  return { active, tryBegin, move, end }
}
