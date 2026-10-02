/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeRange } from '../components/TimeSeriesGraph'
import { MIN_ZOOM_SAMPLES, MIN_ZOOM_TIME_RANGE_SECONDS } from '../components/constants'
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

function nowInSeconds(): number {
  return Math.floor(Date.now() / 1000)
}

function drawnEnd(requested: RequestedTimeRange, served: TimeRange, now: number): number {
  const newestClosedSampleTime = snapDownToGrid(now, served.step)
  const reachesIntoTheOpenInterval = requested.end > newestClosedSampleTime
  const end = reachesIntoTheOpenInterval
    ? snapDownToGrid(requested.end, served.step)
    : requested.end
  return Math.min(end, served.end)
}

export function drawnTimeRange(
  requested: RequestedTimeRange,
  served: TimeRange,
  now: number = nowInSeconds()
): TimeRange {
  const end = hasUsableStep(served) ? drawnEnd(requested, served, now) : requested.end
  const collapsesTheWindow = end <= requested.start
  return {
    start: requested.start,
    end: collapsesTheWindow ? requested.end : end,
    step: served.step
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
