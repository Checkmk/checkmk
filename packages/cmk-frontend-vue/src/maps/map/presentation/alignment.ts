/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { PresentationElement } from '@/maps/types/api'

import type { Box, SlidePoint } from './geometry'

/** Which edge or centre line of the selection an element lines up on. */
export type AlignMode = 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom'

/** Where an element lands when aligned within the selection's bounding box. */
export function alignedPosition(el: PresentationElement, box: Box, mode: AlignMode): SlidePoint {
  switch (mode) {
    case 'left':
      return { x: box.x, y: el.y }
    case 'center':
      return { x: box.x + box.w / 2 - el.w / 2, y: el.y }
    case 'right':
      return { x: box.x + box.w - el.w, y: el.y }
    case 'top':
      return { x: el.x, y: box.y }
    case 'middle':
      return { x: el.x, y: box.y + box.h / 2 - el.h / 2 }
    case 'bottom':
      return { x: el.x, y: box.y + box.h - el.h }
  }
}

/**
 * Even out the gaps between three or more elements along one axis, leaving the
 * outermost two where they are. Fewer than three has nothing to distribute.
 */
export function distributedPositions(
  els: PresentationElement[],
  axis: 'x' | 'y'
): Map<string, number> {
  const sizeKey = axis === 'x' ? 'w' : 'h'
  const ordered = [...els].sort((a, b) => a[axis] - b[axis])
  const head = ordered[0]
  const tail = ordered[ordered.length - 1]
  if (ordered.length < 3 || !head || !tail) {
    return new Map()
  }
  const first = head[axis]
  const last = tail[axis] + tail[sizeKey]
  const occupied = ordered.reduce((sum, el) => sum + el[sizeKey], 0)
  const gap = (last - first - occupied) / (ordered.length - 1)

  const positions = new Map<string, number>()
  let cursor = first
  for (const el of ordered) {
    positions.set(el.id, Math.round(cursor))
    cursor += el[sizeKey] + gap
  }
  return positions
}
