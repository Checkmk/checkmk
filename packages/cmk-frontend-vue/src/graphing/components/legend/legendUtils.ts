/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HorizontalLine, Metric, UnitFormat } from '../TimeSeriesGraph'
import { valueRenderer } from '../TimeSeriesGraph/valueRenderer'

export interface MetricStats {
  min: string
  avg: string
  max: string
  last: string
}

/** `axisUnit` overrides the metric's own unit, so the legend cannot contradict the axis. */
export function metricStats(
  metric: Metric,
  valueResolution: number | null = null,
  axisUnit: UnitFormat | null = null
): MetricStats {
  const fmt = valueRenderer(axisUnit ?? metric.metadata.unit, valueResolution)
  const points = metric.data_points
  if (points.length === 0) {
    return { min: 'n/a', avg: 'n/a', max: 'n/a', last: 'n/a' }
  }
  let min = Infinity
  let max = -Infinity
  let sum = 0
  let count = 0
  let last: number | null = null
  for (const value of points) {
    if (value !== null && isFinite(value)) {
      if (value < min) {
        min = value
      }
      if (value > max) {
        max = value
      }
      sum += value
      count++
      last = value
    }
  }
  return {
    min: isFinite(min) ? fmt(min) : 'n/a',
    avg: count > 0 ? fmt(sum / count) : 'n/a',
    max: isFinite(max) ? fmt(max) : 'n/a',
    last: last !== null ? fmt(last) : 'n/a'
  }
}

export function horizontalLineValue(
  line: HorizontalLine,
  valueResolution: number | null = null,
  axisUnit: UnitFormat | null = null
): string {
  return valueRenderer(axisUnit ?? line.unit, valueResolution)(line.value)
}

export function withNameToggled(hiddenNames: string[], name: string): string[] {
  if (hiddenNames.includes(name)) {
    return hiddenNames.filter((hiddenName) => hiddenName !== name)
  }
  return [...hiddenNames, name]
}
