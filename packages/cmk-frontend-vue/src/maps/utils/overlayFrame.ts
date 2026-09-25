/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type CSSProperties, type ComputedRef, type Ref, computed, ref, watch } from 'vue'

/**
 * The box a ``position: fixed`` overlay's ``left``/``top`` are measured from,
 * in viewport coordinates.
 *
 * Embedded in the Checkmk page that box is the content area, not the viewport
 * (``.maps-app--embed`` sets ``contain: layout``). Pointer and anchor positions
 * are viewport coordinates, so they have to be shifted by its origin, and the
 * room an overlay has ends where the Checkmk sidebars begin.
 */
export function overlayFrameOf(overlay: HTMLElement): DOMRect {
  return (
    overlay.offsetParent?.getBoundingClientRect() ??
    new DOMRect(0, 0, window.innerWidth, window.innerHeight)
  )
}

/**
 * ``left``/``top`` for a fixed overlay that opens at a pointer position given
 * in viewport coordinates.
 */
export function usePointerOverlayStyle(
  overlay: Readonly<Ref<HTMLElement | null>>,
  point: () => { x: number; y: number } | null | undefined
): ComputedRef<CSSProperties> {
  const origin = ref({ left: 0, top: 0 })
  watch(
    overlay,
    (el) => {
      if (el) {
        const frame = overlayFrameOf(el)
        origin.value = { left: frame.left, top: frame.top }
      }
    },
    { flush: 'post', immediate: true }
  )
  return computed(() => {
    const p = point()
    return p ? { left: `${p.x - origin.value.left}px`, top: `${p.y - origin.value.top}px` } : {}
  })
}
