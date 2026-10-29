/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Value-axis (y) domain computation: the value extent the y-axis must cover, derived from the
// buckets that will be drawn.

export interface DomainFlags {
  symmetric?: boolean
}

export interface DomainBucket {
  gap: boolean
  minValue: number
  maxValue: number
}

// A series computed per window, such as a histogram quantile interpolated inside one bucket, lands
// on 0.00475 or an ulp beside it. A domain that narrow cannot be labelled: its label spacing is
// finer than the precision of the values it sits at.
const FLAT_RELATIVE_TOLERANCE = 1e-12

function isFlat(yMin: number, yMax: number): boolean {
  return yMax - yMin <= FLAT_RELATIVE_TOLERANCE * Math.max(Math.abs(yMin), Math.abs(yMax))
}

export function computeYDomain(
  metricsBuckets: DomainBucket[][],
  flags: DomainFlags = {}
): [number, number] {
  let yMin = Infinity
  let yMax = -Infinity
  for (const buckets of metricsBuckets) {
    for (const bucket of buckets) {
      if (bucket.gap) {
        continue
      }
      if (bucket.minValue < yMin) {
        yMin = bucket.minValue
      }
      if (bucket.maxValue > yMax) {
        yMax = bucket.maxValue
      }
    }
  }
  if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) {
    return [0, 1]
  }
  if (flags.symmetric) {
    const extent = Math.max(Math.abs(yMin), Math.abs(yMax))
    const bound = extent === 0 ? 1 : extent
    return [-bound, bound]
  }
  if (isFlat(yMin, yMax)) {
    if (yMin === 0) {
      return [0, 1]
    }
    return yMin > 0 ? [0, 2 * yMin] : [2 * yMin, 0]
  }
  return [yMin, yMax]
}
