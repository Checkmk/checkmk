/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeRange } from '../components/TimeSeriesGraph'
import {
  LEADING_NEIGHBOUR_STEPS,
  MIN_ZOOM_SAMPLES,
  MIN_ZOOM_TIME_RANGE_SECONDS,
  TRAILING_NEIGHBOUR_STEPS
} from '../components/constants'
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

// Whether the user's window is shorter than the interval between two values the backend served.
function isNarrowerThanServedStep(requested: RequestedTimeRange, served: TimeRange): boolean {
  return requested.end - requested.start < served.step
}

// A window narrower than the served step has no grid boundary of its own to snap to: snapping
// would collapse it to nothing drawable, while the value covering it draws across it as it is.
export function drawnTimeRange(requested: RequestedTimeRange, served: TimeRange): TimeRange {
  const { step } = served
  if (!hasUsableStep(served) || isNarrowerThanServedStep(requested, served)) {
    return { start: requested.start, end: requested.end, step }
  }
  return {
    start: snapDownToGrid(requested.start, step),
    end: Math.min(snapDownToGrid(requested.end, step), served.end),
    step
  }
}

// A fetch is answered at its RRA's resolution, coarser the further back it reaches; fewer than
// MIN_ZOOM_SAMPLES of those is too narrow to label. Without a step the configured minimum stands.
export function minZoomSpan(served: TimeRange | undefined): number {
  if (served === undefined || !hasUsableStep(served)) {
    return MIN_ZOOM_TIME_RANGE_SECONDS
  }
  return Math.max(MIN_ZOOM_TIME_RANGE_SECONDS, MIN_ZOOM_SAMPLES * served.step)
}
