/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Value-axis (y) domain computation: the value extent the y-axis must cover, derived from the
// buckets that will be drawn. computeYDomain mirrors the backend's _compute_v_axis_min_max in
// cmk/gui/graphing/rendering/_artwork.py (faithful to its min/max and symmetric handling).

export interface DomainFlags {
  symmetric?: boolean
}

interface DomainBucket {
  gap: boolean
  minValue: number
  maxValue: number
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
    const bound = extent === 0 ? 0.5 : extent
    return [-bound, bound]
  }
  if (yMin === yMax) {
    return [yMin - 0.5, yMax + 0.5]
  }
  return [yMin, yMax]
}
