/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Put irregularly polled metric samples on the regular time grid a
 * ``TimeSeriesGraph`` draws.
 *
 * The daemon streams a sample whenever it polls, so a series is a list of
 * ``{ts, value}`` at whatever cadence the connection ran at. The graph instead
 * takes one value per grid slot (``data_points[i]`` is the sample at
 * ``start + i * step``), so the two have to be reconciled somewhere. Doing it
 * here keeps the graph a pure renderer and keeps the reconciliation testable.
 */
import type { MetricPoint } from '@/maps/types/api'

/** The regular grid a set of series is drawn on. */
export interface SampleGrid {
  /** Unix seconds of ``data_points[0]``. */
  start: number
  /** Unix seconds one step past the last slot. */
  end: number
  /** Slot width in seconds. */
  step: number
  /** Number of slots, i.e. the length every series is resampled to. */
  count: number
}

const MIN_STEP_SECS = 1
/**
 * Cap on the slot count. A graph is a few hundred pixels wide, so a finer grid
 * would only cost memory and rendering time.
 */
const MAX_SLOTS = 600

/**
 * The polling cadence of a set of series, as the median gap between samples.
 *
 * The median rather than the mean: a connection that was down for a while
 * leaves one huge gap, and averaging that in would coarsen the whole grid.
 */
export function samplingIntervalSecs(series: MetricPoint[][]): number | null {
  const gaps: number[] = []
  for (const points of series) {
    for (let i = 1; i < points.length; i++) {
      const gap = points[i]!.ts - points[i - 1]!.ts
      if (gap > 0) {
        gaps.push(gap)
      }
    }
  }
  if (gaps.length === 0) {
    return null
  }
  gaps.sort((a, b) => a - b)
  return gaps[Math.floor(gaps.length / 2)]!
}

/**
 * The grid for a window of ``windowSecs`` ending at ``nowSecs``, resolved at the
 * series' own polling cadence (so no slot invents a sample the connection never
 * took) but never finer than ``MAX_SLOTS`` allows.
 */
export function deriveGrid(
  series: MetricPoint[][],
  windowSecs: number,
  nowSecs: number
): SampleGrid {
  const window = Math.max(windowSecs, MIN_STEP_SECS)
  const floor = Math.ceil(window / MAX_SLOTS)
  const step = Math.max(Math.round(samplingIntervalSecs(series) ?? floor), floor, MIN_STEP_SECS)
  const count = Math.max(1, Math.ceil(window / step))
  const end = Math.floor(nowSecs / step) * step
  const start = end - (count - 1) * step
  return { start, end: start + count * step, step, count }
}

/**
 * One series on ``grid``: every sample goes to its nearest slot, slots the
 * connection has no sample for stay ``null`` so the graph draws a gap instead of
 * bridging one. Samples sharing a slot (jitter, or a cadence finer than the
 * capped grid) are averaged.
 */
export function resampleOnGrid(points: MetricPoint[], grid: SampleGrid): (number | null)[] {
  const sums = new Float64Array(grid.count)
  const counts = new Uint32Array(grid.count)
  for (const point of points) {
    const slot = Math.round((point.ts - grid.start) / grid.step)
    if (slot < 0 || slot >= grid.count) {
      continue
    }
    sums[slot]! += point.value
    counts[slot]! += 1
  }
  return Array.from({ length: grid.count }, (_unused, slot) =>
    counts[slot] === 0 ? null : sums[slot]! / counts[slot]!
  )
}
