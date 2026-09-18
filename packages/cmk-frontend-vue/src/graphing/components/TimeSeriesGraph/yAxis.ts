/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Metric, YAxis } from './types'

/**
 * Derive the y-axis (its unit) from the drawn metrics.
 *
 * Template, single-timeseries and combined graphs draw every curve in a single unit (enforced
 * backend-side), so the axis unit is the unit of any metric. Returns null when there is no metric
 * to take a unit from; the renderer then falls back to raw, unit-less numeric ticks.
 */
export function deriveYAxis(metrics: Metric[], yAxis?: YAxis | null): YAxis | null {
  if (yAxis?.unit) {
    return yAxis
  }
  const unit = metrics[0]?.metadata.unit
  const derivedFromMetrics = unit === undefined ? null : { unit }
  return yAxis && derivedFromMetrics ? { ...yAxis, ...derivedFromMetrics } : derivedFromMetrics
}
