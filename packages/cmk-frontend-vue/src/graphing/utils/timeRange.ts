/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeRange } from '../components/TimeSeriesGraph'
import { LEADING_NEIGHBOUR_STEPS, TRAILING_NEIGHBOUR_STEPS } from '../components/constants'
import type { RequestedTimeRange } from '../types'

export function sameRequestedTimeRange(a: RequestedTimeRange, b: RequestedTimeRange): boolean {
  return a.start === b.start && a.end === b.end
}

function snapDownToGrid(time: number, step: number): number {
  return Math.floor(time / step) * step
}

function hasUsableStep(range: TimeRange): boolean {
  return Number.isFinite(range.step) && range.step > 0
}

export function withEdgeNeighbours(window: TimeRange): TimeRange {
  return {
    start: window.start - LEADING_NEIGHBOUR_STEPS * window.step,
    end: window.end + TRAILING_NEIGHBOUR_STEPS * window.step,
    step: window.step
  }
}

export function drawnTimeRange(requested: RequestedTimeRange, served: TimeRange): TimeRange {
  const { step } = served
  if (!hasUsableStep(served)) {
    return { start: requested.start, end: requested.end, step }
  }
  return {
    start: snapDownToGrid(requested.start, step),
    end: Math.min(snapDownToGrid(requested.end, step), served.end),
    step
  }
}
