/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readonly, ref, watch } from 'vue'

import type { MapElement } from '@/maps/types/api'

/** Below this much pointer travel the header still counts as clicked. */
const DRAG_THRESHOLD = 4

/**
 * Drag behaviour for the object-properties card. The header is a drag handle
 * that offsets the card from where it opened, with a 4-px threshold so a plain
 * header click still works. The header stays inside ``frame``, so the card can
 * always be pulled back. The offset resets whenever the object swaps.
 */
export function useDraggableCard(object: () => MapElement, frame: () => HTMLElement | null) {
  const offset = ref({ dx: 0, dy: 0 })
  const dragStart = ref<{
    px: number
    py: number
    ox: number
    oy: number
    dx: [number, number]
    dy: [number, number]
  } | null>(null)
  const dragging = ref(false)

  function onHeaderPointerDown(e: PointerEvent) {
    if (e.button !== 0) {
      return
    }
    // Don't start a drag from interactive children (the close button etc.).
    if ((e.target as HTMLElement).closest('button')) {
      return
    }
    const { dx: ox, dy: oy } = offset.value
    const header = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const bounds = frame()?.getBoundingClientRect() ?? header
    dragStart.value = {
      px: e.clientX,
      py: e.clientY,
      ox,
      oy,
      dx: [ox + bounds.left - header.left, ox + bounds.right - header.right],
      dy: [oy + bounds.top - header.top, oy + bounds.bottom - header.bottom]
    }
  }

  function onHeaderPointerMove(e: PointerEvent) {
    const s = dragStart.value
    if (!s) {
      return
    }
    // A press that left the header before the drag took the pointer ended
    // where the header never heard of it.
    if (e.buttons === 0) {
      onHeaderPointerUp()
      return
    }
    const dx = clamp(s.ox + (e.clientX - s.px), s.dx)
    const dy = clamp(s.oy + (e.clientY - s.py), s.dy)
    if (
      !dragging.value &&
      Math.abs(dx - s.ox) < DRAG_THRESHOLD &&
      Math.abs(dy - s.oy) < DRAG_THRESHOLD
    ) {
      return
    }
    if (!dragging.value) {
      dragging.value = true
      const target = e.currentTarget as HTMLElement
      try {
        target.setPointerCapture(e.pointerId)
      } catch {
        // pointer may have ended
      }
    }
    offset.value = { dx, dy }
  }

  function onHeaderPointerUp() {
    dragStart.value = null
    dragging.value = false
  }

  watch(object, () => {
    offset.value = { dx: 0, dy: 0 }
    onHeaderPointerUp()
  })

  return {
    dragOffset: readonly(offset),
    dragging,
    onHeaderPointerDown,
    onHeaderPointerMove,
    onHeaderPointerUp
  }
}

function clamp(value: number, [min, max]: [number, number]): number {
  return Math.min(Math.max(value, min), max)
}
