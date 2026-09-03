/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type Ref, computed, onMounted, onUnmounted, ref, watch } from 'vue'

import type { MapElement } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'

/** How close to the edge of the area the card may come. */
const EDGE_MARGIN = 12

/** Below this much pointer travel the header still counts as clicked. */
const DRAG_THRESHOLD = 4

interface PropertiesPopoverOptions {
  anchorRect: () => AnchorRect | null | undefined
  object: () => MapElement
  /** The card itself, so it is placed by its real size. */
  card: Ref<HTMLElement | null>
}

/**
 * The box the card's ``left``/``top`` are measured from, in viewport
 * coordinates, or ``null`` while the card cannot be measured.
 *
 * Embedded in the Checkmk page, the SPA's overlays are contained by the content
 * area rather than the viewport (``.maps-app--embed`` sets ``contain: layout``),
 * so the card's own offset parent — not the window — says both where its
 * coordinates start and how much room there is. Guessing the window instead
 * would place the card in the wrong coordinate space, off by the sidebar.
 */
function positioningFrame(card: HTMLElement | null): DOMRect | null {
  return card?.offsetParent?.getBoundingClientRect() ?? null
}

/**
 * Placement + drag behaviour for the object-properties card. With an anchor it
 * renders as a popover beside the clicked object (preferring the right side,
 * clamped inside the map area); without one it is a centered modal. The header
 * is a drag handle that offsets the card via a transform, with a 4-px threshold
 * so a plain header click still works. The offset resets whenever the object
 * swaps.
 */
export function usePropertiesPopover(options: PropertiesPopoverOptions) {
  const { anchorRect, object, card } = options

  const isPopover = computed(() => !!anchorRect())

  const popoverStyle = ref<Record<string, string>>({})

  function place(): void {
    // Read through the getter every time: the caller keeps it tracking the
    // object, which moves whenever the canvas re-lays out under the card.
    const r = anchorRect() ?? null
    const frame = positioningFrame(card.value)
    if (!r || !frame) {
      // Nothing to sit beside, or nothing measurable yet — placing on a
      // guessed frame would put the card in the wrong coordinate space.
      popoverStyle.value = {}
      return
    }
    const width = card.value!.offsetWidth
    const height = card.value!.offsetHeight

    // Both edges are clamped: the card is wider than the gap beside an object
    // near either side.
    const maxLeft = Math.max(EDGE_MARGIN, frame.width - width - EDGE_MARGIN)
    const preferred = r.right - frame.left + EDGE_MARGIN
    const left = preferred <= maxLeft ? preferred : r.left - frame.left - EDGE_MARGIN - width

    const maxTop = Math.max(EDGE_MARGIN, frame.height - height - EDGE_MARGIN)

    popoverStyle.value = {
      left: `${Math.min(Math.max(left, EDGE_MARGIN), maxLeft)}px`,
      top: `${Math.min(Math.max(r.top - frame.top, EDGE_MARGIN), maxTop)}px`
    }
  }

  const dragOffset = ref({ dx: 0, dy: 0 })
  const dragStart = ref<{ px: number; py: number; ox: number; oy: number } | null>(null)
  const dragging = ref(false)

  const cardStyle = computed<Record<string, string>>(() => {
    const base: Record<string, string> = isPopover.value ? { ...popoverStyle.value } : {}
    if (dragOffset.value.dx !== 0 || dragOffset.value.dy !== 0) {
      base.transform = `translate(${dragOffset.value.dx}px, ${dragOffset.value.dy}px)`
    }
    return base
  })

  function onHeaderPointerDown(e: PointerEvent) {
    if (e.button !== 0) {
      return
    }
    // Don't start a drag from interactive children (the close button etc.).
    if ((e.target as HTMLElement).closest('button')) {
      return
    }
    dragStart.value = {
      px: e.clientX,
      py: e.clientY,
      ox: dragOffset.value.dx,
      oy: dragOffset.value.dy
    }
  }

  function onHeaderPointerMove(e: PointerEvent) {
    const s = dragStart.value
    if (!s) {
      return
    }
    const dx = s.ox + (e.clientX - s.px)
    const dy = s.oy + (e.clientY - s.py)
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
    dragOffset.value = { dx, dy }
  }

  function onHeaderPointerUp() {
    dragStart.value = null
    dragging.value = false
  }

  /**
   * Re-place after something other than the operator changed: a section folded
   * open, the window resized. Once the card has been dragged aside, that
   * placement is the operator's and re-placing would snatch it back to the
   * object.
   */
  function replaceUnlessDragged(): void {
    if (dragOffset.value.dx === 0 && dragOffset.value.dy === 0) {
      place()
    }
  }

  watch(() => anchorRect(), place)
  // A fresh card measures nothing until it is in the DOM; from then on the
  // observer keeps it inside as the sections it shows grow and shrink it.
  watch(card, place)
  useResizeObserver(replaceUnlessDragged).observe(card)

  watch(object, () => {
    dragOffset.value = { dx: 0, dy: 0 }
    dragStart.value = null
  })

  onMounted(() => window.addEventListener('resize', replaceUnlessDragged, { passive: true }))
  onUnmounted(() => window.removeEventListener('resize', replaceUnlessDragged))

  return {
    isPopover,
    cardStyle,
    dragging,
    onHeaderPointerDown,
    onHeaderPointerMove,
    onHeaderPointerUp
  }
}
