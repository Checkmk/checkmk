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

/** Travel, in screen pixels, before a press counts as a pan. */
const PAN_THRESHOLD = 4

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
    pointerId = event.pointerId
    scroller = target
    fromX = event.clientX
    fromY = event.clientY
    fromScrollLeft = target.scrollLeft
    fromScrollTop = target.scrollTop
    return true
  }

  function move(event: PointerEvent): boolean {
    if (!scroller || event.pointerId !== pointerId) {
      return false
    }
    // Released outside the canvas, where no pointerup reaches it.
    if ((event.buttons & 1) === 0) {
      end()
      return false
    }
    const dx = event.clientX - fromX
    const dy = event.clientY - fromY
    if (!active.value) {
      if (Math.abs(dx) <= PAN_THRESHOLD && Math.abs(dy) <= PAN_THRESHOLD) {
        return true
      }
      active.value = true
      // Grab the pointer only now: capturing on press would redirect a plain
      // click, e.g. on a link in a hover card, to the canvas.
      if (pointerId !== null) {
        source.canvas()?.setPointerCapture(pointerId)
      }
    }
    scroller.scrollLeft = fromScrollLeft - dx
    scroller.scrollTop = fromScrollTop - dy
    return true
  }

  /** Whether the press turned into a pan, so that its click must be dropped. */
  function end(): boolean {
    if (!scroller) {
      return false
    }
    const panned = active.value
    active.value = false
    if (panned && pointerId !== null) {
      try {
        source.canvas()?.releasePointerCapture(pointerId)
      } catch {
        // The pointer may already have been released.
      }
    }
    pointerId = null
    scroller = null
    return panned
  }

  return { active, tryBegin, move, end }
}
