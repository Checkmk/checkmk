/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Rubber-band selection on the empty canvas in edit mode.
 *
 * The rectangle is tracked in canvas-relative pixels, because that is what it
 * is drawn in; only the hit test at the end converts to map coordinates. It
 * grabs the pointer as soon as the drag is unambiguous, so releasing outside
 * the canvas still completes the selection.
 */
import type { ComputedRef } from 'vue'

import { type MarqueeRect, useMarquee } from '@/maps/map/composables/useMarquee'
import type { MapElement } from '@/maps/types/api'

export interface CanvasMarqueeSelect {
  visible: ComputedRef<boolean>
  rect: ComputedRef<MarqueeRect>
  /** Take the gesture, or leave it for the next handler. */
  tryBegin: (event: PointerEvent) => boolean
  move: (event: PointerEvent) => boolean
  end: () => boolean
}

export function useCanvasMarqueeSelect(source: {
  canvas: () => HTMLElement | null
  objects: () => MapElement[]
  toMapCoords: (offsetX: number, offsetY: number, rect: DOMRect) => { x: number; y: number }
  onSelect: (ids: string[], additive: boolean) => void
  /** Report that the click closing this gesture must not deselect. */
  onConsumedClick: () => void
}): CanvasMarqueeSelect {
  const marquee = useMarquee()
  let pointerId: number | null = null

  function capture(): void {
    if (pointerId === null) {
      return
    }
    try {
      source.canvas()?.setPointerCapture(pointerId)
    } catch {
      // The pointer may have ended already.
    }
  }

  function tryBegin(event: PointerEvent): boolean {
    const canvas = source.canvas()
    // A press on an object starts a drag, not a selection.
    if (!canvas || (event.target as HTMLElement | null)?.closest('[data-object-id]')) {
      return false
    }
    const rect = canvas.getBoundingClientRect()
    marquee.begin(
      event.clientX - rect.left,
      event.clientY - rect.top,
      event.shiftKey || event.ctrlKey || event.metaKey
    )
    pointerId = event.pointerId
    return true
  }

  function move(event: PointerEvent): boolean {
    const canvas = source.canvas()
    if (!marquee.active.value || !canvas) {
      return false
    }
    const rect = canvas.getBoundingClientRect()
    if (marquee.update(event.clientX - rect.left, event.clientY - rect.top)) {
      capture()
    }
    return true
  }

  function end(): boolean {
    if (!marquee.active.value) {
      return false
    }
    const moved = marquee.moved.value
    const box = marquee.rect.value
    const additive = marquee.additive.value
    marquee.reset()
    const released = pointerId
    pointerId = null
    if (released !== null) {
      try {
        source.canvas()?.releasePointerCapture(released)
      } catch {
        // The pointer may already have been released.
      }
    }
    const canvas = source.canvas()
    if (!moved || !canvas) {
      return true
    }
    const rect = canvas.getBoundingClientRect()
    const from = source.toMapCoords(box.left, box.top, rect)
    const to = source.toMapCoords(box.left + box.width, box.top + box.height, rect)
    // Lines are selected by clicking them: they have two ends, so "inside the
    // rectangle" has no single answer.
    const ids = source
      .objects()
      .filter(
        (object) =>
          object.type !== 'line' &&
          object.x >= from.x &&
          object.x <= to.x &&
          object.y >= from.y &&
          object.y <= to.y
      )
      .map((object) => object.id)
    source.onSelect(ids, additive)
    source.onConsumedClick()
    return true
  }

  return { visible: marquee.visible, rect: marquee.rect, tryBegin, move, end }
}
