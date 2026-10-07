/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeRange } from '../components/TimeSeriesGraph'
import { MIN_ZOOM_SAMPLES, MIN_ZOOM_TIME_RANGE_SECONDS } from '../components/constants'
import type { RequestedTimeRange, TimeRangeCommitKind } from '../types'

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

// The renderer decimates to one M4 bucket per plotted column (TimeSeriesGraph.vue) and draws into a
// DPR-scaled bitmap, so a single sample per column collapses each bucket's min/max and loses the
// detail between samples. Requesting several samples per column keeps that detail. RRD serves this
// for free — RRDConsolidate never returns finer than the RRA step — while query backends honour the
// step literally, bounding a request at ~4x the plotted width in points.
const SAMPLES_PER_PLOTTED_COLUMN = 4

function computeStep(start: number, end: number, canvasWidth: number): number {
  return Math.max(60, Math.ceil((end - start) / (canvasWidth * SAMPLES_PER_PLOTTED_COLUMN)))
}

/** Plans the window to fetch for the requested range at the plotted width. */
export type FetchWindowPlanner = (range: RequestedTimeRange, canvasWidth: number) => TimeRange

/** Spans the requested range at a step that gives each plotted column several samples. */
export const planFetchWindowByWidth: FetchWindowPlanner = (range, canvasWidth) => ({
  start: range.start,
  end: range.end,
  step: computeStep(range.start, range.end, canvasWidth)
})

/** The requested range a zoom or pan commits: a pan keeps the asked span. */
export function committedTimeRange(
  asked: RequestedTimeRange,
  committed: RequestedTimeRange,
  kind: TimeRangeCommitKind
): RequestedTimeRange {
  // The drawn window differs from the asked one; adopting its span would change it on every pan.
  const end =
    kind === 'translated_timerange' ? committed.start + (asked.end - asked.start) : committed.end
  return { start: committed.start, end }
}

/** How a graph plans its fetch and draws its window along the time axis. */
export interface TimeAxis {
  planFetchWindow: FetchWindowPlanner
  drawnTimeRange(requested: RequestedTimeRange, served: TimeRange): TimeRange
  /** The shortest span a time zoom may reach, given the host's own minimum. */
  minSpan(hostMinimum: number | null): number | null
}

/** A time axis that draws the samples where they lie. */
export function continuousTimeAxis(): TimeAxis {
  return {
    planFetchWindow: planFetchWindowByWidth,
    drawnTimeRange: (requested, served) => drawnTimeRange(requested, served),
    minSpan: (hostMinimum) => hostMinimum
  }
}
