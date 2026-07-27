/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type ZoomMode = 'time' | 'value'

// Widen [from,to] symmetrically so it is at least `floor` wide. A null floor (no
// minimum configured) is a no-op. Used to enforce the minimum zoom span/value so a
// tiny drag does not collapse the window.
export function clampSpan(range: [number, number], floor: number | null): [number, number] {
  const [from, to] = range
  if (floor === null || to - from >= floor) {
    return [from, to]
  }
  const mid = (from + to) / 2
  return [mid - floor / 2, mid + floor / 2]
}

export interface PlotBox {
  left: number
  top: number
  width: number
  height: number
}

export interface SelectionPoints {
  x0: number
  y0: number
  x1: number
  y1: number
}

export interface SelectionRect {
  x: number
  y: number
  width: number
  height: number
}

function clamp(value: number, lo: number, hi: number): number {
  return Math.min(Math.max(value, lo), hi)
}

// A drag is tracked on the window, so it can end outside the plot, and d3 scales
// extrapolate past their range rather than saturating.
export function clampPixelToPlot(pixel: number, plotExtent: number): number {
  return clamp(pixel, 0, plotExtent)
}

export function selectionRect(
  mode: ZoomMode,
  points: SelectionPoints,
  plot: PlotBox
): SelectionRect {
  const right = plot.left + plot.width
  const bottom = plot.top + plot.height
  const x0 = clamp(points.x0, plot.left, right)
  const x1 = clamp(points.x1, plot.left, right)
  const y0 = clamp(points.y0, plot.top, bottom)
  const y1 = clamp(points.y1, plot.top, bottom)
  if (mode === 'time') {
    return { x: Math.min(x0, x1), y: plot.top, width: Math.abs(x1 - x0), height: plot.height }
  }
  return { x: plot.left, y: Math.min(y0, y1), width: plot.width, height: Math.abs(y1 - y0) }
}
