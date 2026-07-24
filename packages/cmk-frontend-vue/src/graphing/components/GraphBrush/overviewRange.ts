/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeInterval } from '../../types'
import type { TimeRange } from '../TimeSeriesGraph'

export function overviewMultiplier(spanSeconds: number): number {
  if (spanSeconds <= 25 * 3600) {
    return 7
  }
  if (spanSeconds <= 8 * 86_400) {
    return 5
  }
  return 3
}

function clampExtent(start: number, end: number, now: number, earliest?: number): TimeInterval {
  const width = end - start
  if (end > now) {
    end = now
    start = now - width
  }
  if (earliest !== undefined && start < earliest) {
    start = earliest
    end = earliest + width
  }
  return { start, end }
}

function centerExtent(window: TimeInterval, width: number): TimeInterval {
  const start = Math.round((window.start + window.end - width) / 2)
  return { start, end: start + width }
}

export function overviewDomain(
  committed: TimeInterval,
  nowSeconds: number,
  earliest?: number
): TimeInterval {
  const span = committed.end - committed.start
  const width = Math.round(span * overviewMultiplier(span))
  const centered = centerExtent(committed, width)
  return clampExtent(centered.start, centered.end, nowSeconds, earliest)
}

// How close to an edge, as a fraction of strip width, the window may sit before the strip recenters.
export const DEFAULT_EDGE_FRACTION = 0.1

export function recenterOverviewDomain(
  domain: TimeInterval,
  window: TimeInterval,
  nowSeconds: number,
  edgeFraction = DEFAULT_EDGE_FRACTION,
  earliest?: number
): TimeInterval {
  const width = domain.end - domain.start
  const leftEdge = domain.start + edgeFraction * width
  const rightEdge = domain.end - edgeFraction * width
  if (window.start >= leftEdge && window.end <= rightEdge) {
    return domain
  }
  const centered = centerExtent(window, width)
  return clampExtent(centered.start, centered.end, nowSeconds, earliest)
}

export function overviewStep(start: number, end: number, canvasWidth: number): number {
  return Math.max(60, Math.ceil((end - start) / canvasWidth))
}

export function overviewTimeRange(
  committed: TimeRange,
  nowSeconds: number,
  canvasWidth: number
): TimeRange {
  const { start, end } = overviewDomain(committed, nowSeconds)
  return { start, end, step: overviewStep(start, end, canvasWidth) }
}
