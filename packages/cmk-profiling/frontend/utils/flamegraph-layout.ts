/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FlamegraphNode, LayoutRect } from '../types'

const MAX_RECTS = 10_000
const MIN_WIDTH_PX = 2
const FRAME_HEIGHT = 50
const FRAME_V_GAP = 2

export { FRAME_HEIGHT }

export interface LayoutResult {
  rects: LayoutRect[]
  height: number
}

/**
 * Compute layout rectangles from a flamegraph tree.
 * Returns top-down (icicle-style) layout — depth 0 is the top.
 */
export function layoutFlamegraph(
  root: FlamegraphNode,
  canvasWidth: number,
  maxDepth: number = 10
): LayoutResult {
  if (root.total <= 0 && root.children.length === 0) {
    return { rects: [], height: 60 }
  }

  const rects: LayoutRect[] = []
  // Icicle scaling by cumulative time: each child's width is parent_width *
  // (child.cumtime / parent.cumtime). The "missing" slice (parent.cumtime
  // minus the children's cumtimes) shows up as empty space and represents
  // the parent's own self-time.
  // Fallback to siblings-relative sizing for the synthetic root (no
  // meaningful total) and for nodes whose children's cumtimes overflow the
  // parent (shared callees appear under multiple parents).
  const stack: Array<{ node: FlamegraphNode; x: number; width: number; depth: number }> = [
    { node: root, x: 0, width: canvasWidth, depth: 0 }
  ]

  while (stack.length > 0 && rects.length < MAX_RECTS) {
    const { node, x, width, depth } = stack.pop()!
    const siblingsTotal = node.children.reduce((sum, c) => sum + c.total, 0)
    const denom = node.total > 0 && node.total >= siblingsTotal ? node.total : siblingsTotal
    let cx = x

    for (const child of node.children) {
      let w: number
      if (denom > 0) {
        w = Math.max((child.total / denom) * width, MIN_WIDTH_PX)
      } else {
        w = Math.max(width / node.children.length, MIN_WIDTH_PX)
      }

      rects.push({
        x: cx,
        y: 0, // will be computed below
        width: w,
        height: FRAME_HEIGHT - FRAME_V_GAP,
        name: child.name,
        selfTime: child.value,
        totalTime: child.total,
        depth: depth,
        node: child
      })

      if (depth < maxDepth - 1) {
        stack.push({ node: child, x: cx, width: w, depth: depth + 1 })
      }
      cx += w
    }
  }

  // Compute Y coordinates top-down (icicle style)
  const actualMaxDepth = rects.reduce((max, r) => Math.max(max, r.depth), 0)
  const topMargin = 10
  const height = topMargin + (actualMaxDepth + 1) * FRAME_HEIGHT + 20

  for (const rect of rects) {
    rect.y = topMargin + rect.depth * FRAME_HEIGHT
  }

  return { rects, height }
}

/**
 * Find the rect under a given point. Returns index or -1.
 */
export function hitTest(rects: LayoutRect[], px: number, py: number): number {
  for (let i = rects.length - 1; i >= 0; i--) {
    const r = rects[i]!
    if (px >= r.x && px <= r.x + r.width && py >= r.y && py <= r.y + r.height) {
      return i
    }
  }
  return -1
}
