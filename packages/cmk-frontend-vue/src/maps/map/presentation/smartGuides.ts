/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Box } from './geometry'

export interface Guide {
  axis: 'x' | 'y'
  pos: number
  start: number
  end: number
}

export interface GuideResult {
  dx: number
  dy: number
  guides: Guide[]
}

function xAnchors(b: Box): number[] {
  return [b.x, b.x + b.w / 2, b.x + b.w]
}

function yAnchors(b: Box): number[] {
  return [b.y, b.y + b.h / 2, b.y + b.h]
}

// Snap the moving box to the edges/centers of the other boxes. Returns the
// nudge (dx/dy) that lands the closest within-threshold anchor pair flush, plus
// the guide lines to paint. Edges and centers both count — that's what makes it
// feel like a design tool rather than grid-snapping.
export function computeSmartGuides(moving: Box, others: Box[], threshold = 6): GuideResult {
  let dx = 0
  let bestX = threshold + 0.001
  let dy = 0
  let bestY = threshold + 0.001
  const guides: Guide[] = []

  const mx = xAnchors(moving)
  const my = yAnchors(moving)

  for (const o of others) {
    for (const ox of xAnchors(o)) {
      for (const m of mx) {
        const dist = Math.abs(ox - m)
        if (dist < bestX) {
          bestX = dist
          dx = ox - m
        }
      }
    }
    for (const oy of yAnchors(o)) {
      for (const m of my) {
        const dist = Math.abs(oy - m)
        if (dist < bestY) {
          bestY = dist
          dy = oy - m
        }
      }
    }
  }

  const snapped: Box = { x: moving.x + dx, y: moving.y + dy, w: moving.w, h: moving.h }
  const sx = xAnchors(snapped)
  const sy = yAnchors(snapped)
  for (const o of others) {
    for (const ox of xAnchors(o)) {
      if (sx.some((m) => Math.abs(m - ox) < 0.5)) {
        guides.push({
          axis: 'x',
          pos: ox,
          start: Math.min(o.y, snapped.y),
          end: Math.max(o.y + o.h, snapped.y + snapped.h)
        })
      }
    }
    for (const oy of yAnchors(o)) {
      if (sy.some((m) => Math.abs(m - oy) < 0.5)) {
        guides.push({
          axis: 'y',
          pos: oy,
          start: Math.min(o.x, snapped.x),
          end: Math.max(o.x + o.w, snapped.x + snapped.w)
        })
      }
    }
  }

  return { dx, dy, guides }
}
