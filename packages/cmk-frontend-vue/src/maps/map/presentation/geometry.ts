/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// The slide's coordinate vocabulary and the maths of a transform gesture.
// Everything here is in slide space (the fixed-size design surface), never in
// screen pixels -- ``useSlideViewport.screenToSlide`` is the one conversion.

/** A point on the slide. */
export interface SlidePoint {
  x: number
  y: number
}

/** An element's axis-aligned box on the slide. */
export interface Box extends SlidePoint {
  w: number
  h: number
}

/** The box a resize or rotate gesture started from. */
export interface TransformOrigin extends Box {
  rotation: number
}

/**
 * The frontmost element covering a point that the caller will accept. Runs on
 * every pointer move of a drag, so it picks the maximum in one pass rather than
 * sorting a filtered copy.
 */
export function topmostAt<T extends Box & { z: number }>(
  elements: readonly T[],
  p: SlidePoint,
  accept: (el: T) => boolean
): T | undefined {
  let best: T | undefined
  for (const el of elements) {
    if (
      p.x >= el.x &&
      p.x <= el.x + el.w &&
      p.y >= el.y &&
      p.y <= el.y + el.h &&
      accept(el) &&
      (!best || el.z > best.z)
    ) {
      best = el
    }
  }
  return best
}

/** Nothing may be resized below this, in slide units. */
const MIN_SIDE = 8

/**
 * The box a resize handle drags out.
 *
 * The pointer delta arrives in slide axes but is projected onto the element's
 * local axes, so a rotated element resizes along its own edges. Because the
 * element rotates around its centre, x/y cannot be patched directly: the local
 * centre shift (the grabbed side moves, the opposite side stays) is rotated
 * into slide space and the box is re-derived from the new centre. That is what
 * keeps the fixed edge truly fixed at any rotation.
 */
export function resizedBox(
  origin: TransformOrigin,
  handle: string,
  delta: SlidePoint,
  keepRatio: boolean
): Box {
  const a = (-(origin.rotation || 0) * Math.PI) / 180
  const dx = delta.x * Math.cos(a) - delta.y * Math.sin(a)
  const dy = delta.x * Math.sin(a) + delta.y * Math.cos(a)

  let w = origin.w
  let h = origin.h
  if (handle.includes('e')) {
    w = origin.w + dx
  }
  if (handle.includes('w')) {
    w = origin.w - dx
  }
  if (handle.includes('s')) {
    h = origin.h + dy
  }
  if (handle.includes('n')) {
    h = origin.h - dy
  }
  w = Math.max(w, MIN_SIDE)
  h = Math.max(h, MIN_SIDE)
  if (keepRatio && origin.w > 0 && origin.h > 0) {
    const ratio = origin.w / origin.h
    if (Math.abs(dx) > Math.abs(dy)) {
      h = w / ratio
    } else {
      w = h * ratio
    }
    // The ratio can derive a side back below the minimum; lift both together
    // rather than clamping one, which would break the ratio being held for.
    const lift = Math.max(MIN_SIDE / w, MIN_SIDE / h, 1)
    w *= lift
    h *= lift
  }

  const lx = handle.includes('w') ? origin.w - w : 0
  const ly = handle.includes('n') ? origin.h - h : 0
  const rad = ((origin.rotation || 0) * Math.PI) / 180
  const dcxL = lx + (w - origin.w) / 2
  const dcyL = ly + (h - origin.h) / 2
  const cx = origin.x + origin.w / 2 + dcxL * Math.cos(rad) - dcyL * Math.sin(rad)
  const cy = origin.y + origin.h / 2 + dcxL * Math.sin(rad) + dcyL * Math.cos(rad)
  return { x: cx - w / 2, y: cy - h / 2, w, h }
}

/**
 * The rotation, in degrees, that points the element's top edge at ``pointer``.
 * Snapping quantises to 15° so an operator can hit the common angles exactly.
 */
export function rotationFor(origin: TransformOrigin, pointer: SlidePoint, snap: boolean): number {
  const cx = origin.x + origin.w / 2
  const cy = origin.y + origin.h / 2
  const deg = (Math.atan2(pointer.y - cy, pointer.x - cx) * 180) / Math.PI + 90
  return Math.round(snap ? Math.round(deg / 15) * 15 : deg)
}
