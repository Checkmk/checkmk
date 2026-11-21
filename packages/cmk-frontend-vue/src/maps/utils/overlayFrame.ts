/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import {
  type CSSProperties,
  type ComputedRef,
  type Ref,
  computed,
  onScopeDispose,
  ref,
  watch
} from 'vue'

import type { AnchorRect } from '@/maps/utils/anchorRect'

/** How close to the edge of the frame an overlay may come. */
const EDGE_MARGIN = 8

/** Room between an overlay and the object it belongs to. */
const ANCHOR_GAP = 8

/** How long an anchor rests before an overlay asks again what it would cover. */
const SETTLE_MS = 150

/** A fixed overlay's frame, in viewport coordinates. */
export interface OverlayFrame {
  /** Where the overlay's ``left``/``top`` are measured from. */
  left: number
  top: number
  /** Where the room it has ends. */
  right: number
  bottom: number
}

// Inside Checkmk's <iframe name="main"> the outer window is often smaller than
// the iframe's own innerHeight, so a position that fits `window.innerHeight`
// can still paint past the visible parent edge.
function visibleBounds(): { width: number; height: number } {
  const fallback = { width: window.innerWidth, height: window.innerHeight }
  if (window === window.top) {
    return fallback
  }
  try {
    const top = window.top
    const frame = window.frameElement as HTMLIFrameElement | null
    if (!top || !frame) {
      return fallback
    }
    const fr = frame.getBoundingClientRect()
    return {
      width: Math.min(fallback.width, top.innerWidth - fr.left),
      height: Math.min(fallback.height, top.innerHeight - fr.top)
    }
  } catch {
    return fallback
  }
}

/**
 * The frame a ``position: fixed`` overlay is placed in.
 *
 * Embedded in the Checkmk page that frame is the content area, not the viewport
 * (``.maps-app--embed`` sets ``contain: layout``). Pointer and anchor positions
 * are viewport coordinates, so they have to be shifted by its origin, and the
 * room an overlay has ends where the Checkmk sidebars begin.
 */
export function overlayFrameOf(overlay: HTMLElement): OverlayFrame {
  const box =
    overlay.offsetParent?.getBoundingClientRect() ??
    new DOMRect(0, 0, window.innerWidth, window.innerHeight)
  const visible = visibleBounds()
  return {
    left: box.left,
    top: box.top,
    right: Math.min(box.right, visible.width),
    bottom: Math.min(box.bottom, visible.height)
  }
}

/** Hidden at the frame's origin while it has no place. */
function placedStyle(
  placed: Readonly<Ref<{ left: number; top: number } | null>>
): ComputedRef<CSSProperties> {
  return computed(() =>
    placed.value
      ? { left: `${placed.value.left}px`, top: `${placed.value.top}px` }
      : { left: '0px', top: '0px', visibility: 'hidden' }
  )
}

/**
 * ``left``/``top`` for a fixed overlay that opens at a pointer position given
 * in viewport coordinates. Where it would run past the frame it opens on the
 * other side instead: of the pointer, or of ``around`` -- the object it belongs
 * to -- so a flipped card does not land on top of that object.
 *
 * It is measured where it stands, so its size must not depend on the room left
 * there: the overlay sizes to its content (``width: max-content``).
 */
export function usePointerOverlayStyle(
  overlay: Readonly<Ref<HTMLElement | null>>,
  point: () => { x: number; y: number } | null | undefined,
  around: () => AnchorRect | null | undefined = () => null
): ComputedRef<CSSProperties> {
  const placed = ref<{ left: number; top: number } | null>(null)
  let flipped: { x: boolean; y: boolean } | null = null

  function place(opens: boolean): void {
    const el = overlay.value
    const p = point()
    if (!el || !p) {
      placed.value = null
      return
    }
    const frame = overlayFrameOf(el)
    const width = el.offsetWidth
    const height = el.offsetHeight
    const a = around()
    if (opens || !flipped || !el.matches(':hover')) {
      flipped = {
        x: p.x + width > frame.right - EDGE_MARGIN,
        y: p.y + height > frame.bottom - EDGE_MARGIN
      }
    }
    const left = flipped.x ? (a ? a.left - ANCHOR_GAP : p.x) - width : p.x
    const top = flipped.y ? (a ? a.top - ANCHOR_GAP : p.y) - height : p.y
    placed.value = {
      left:
        Math.max(frame.left + EDGE_MARGIN, Math.min(frame.right - EDGE_MARGIN - width, left)) -
        frame.left,
      top:
        Math.max(frame.top + EDGE_MARGIN, Math.min(frame.bottom - EDGE_MARGIN - height, top)) -
        frame.top
    }
  }

  // It also grows while it is open -- a menu once its object turns into a
  // problem, a card once it lists more -- which the pointer does not see.
  // Under the pointer it keeps its side and moves only as far as the frame
  // makes it: on the other side it would leave the pointer, which closes it.
  useResizeObserver(() => place(false)).observe(overlay)
  watch([overlay, point, around], () => place(true), { flush: 'post', immediate: true })

  return placedStyle(placed)
}

/**
 * ``left``/``top`` for a fixed overlay centred above an object given in
 * viewport coordinates. Without room above, or where it would cover what
 * ``covers`` says matters and below would not, it goes below, and it is kept
 * inside the frame sideways. While the object is out of the frame altogether
 * the overlay is not shown: it would offer to act on something out of sight.
 *
 * While the object moves at its size, as when it is dragged, the overlay keeps
 * its side and asks ``covers`` again only once the object rests: asking on
 * every frame costs hit tests, and the overlay would jump past each object on
 * the way.
 */
export function useAnchorOverlayStyle(
  overlay: Readonly<Ref<HTMLElement | null>>,
  anchor: () => AnchorRect | null | undefined,
  covers: (rect: AnchorRect) => boolean = () => false
): ComputedRef<CSSProperties> {
  const placed = ref<{ left: number; top: number } | null>(null)
  let above: boolean | null = null
  let lastSize = ''
  let settle: ReturnType<typeof setTimeout> | undefined
  onScopeDispose(() => clearTimeout(settle))

  function place(decides: boolean): void {
    clearTimeout(settle)
    const el = overlay.value
    const a = anchor()
    if (!el || !a) {
      placed.value = null
      return
    }
    const frame = overlayFrameOf(el)
    if (
      a.right < frame.left ||
      a.left > frame.right ||
      a.bottom < frame.top ||
      a.top > frame.bottom
    ) {
      placed.value = null
      return
    }
    const width = el.offsetWidth
    const height = el.offsetHeight
    const centred = (a.left + a.right) / 2 - width / 2
    const left = Math.max(
      frame.left + EDGE_MARGIN,
      Math.min(centred, frame.right - EDGE_MARGIN - width)
    )
    const at = (top: number): AnchorRect => ({
      left,
      top,
      right: left + width,
      bottom: top + height
    })
    const topAbove = a.top - ANCHOR_GAP - height
    const topBelow = a.bottom + ANCHOR_GAP
    const size = `${a.right - a.left}x${a.bottom - a.top}x${width}x${height}`
    if (decides || above === null || size !== lastSize) {
      above = !(covers(at(topAbove)) && !covers(at(topBelow)))
    } else {
      settle = setTimeout(() => place(true), SETTLE_MS)
    }
    lastSize = size
    const top = above && topAbove >= frame.top + EDGE_MARGIN ? topAbove : topBelow
    placed.value = { left: left - frame.left, top: top - frame.top }
  }

  // The overlay's width changes with what it offers, which the anchor does not see.
  useResizeObserver(() => place(true)).observe(overlay)
  watch([overlay, anchor], () => place(false), { flush: 'post', immediate: true })

  return placedStyle(placed)
}
