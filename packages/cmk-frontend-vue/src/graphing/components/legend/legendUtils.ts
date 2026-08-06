/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'

import type { HorizontalLine, Metric } from '../TimeSeriesGraph'

export interface MetricStats {
  min: string
  avg: string
  max: string
  last: string
}

/** Formatted min/avg/max/last over the series' present data points; 'n/a' where absent. */
export function metricStats(metric: Metric): MetricStats {
  const { formatter } = userSpecificUnit(metric.metadata.unit, 'celsius')
  const fmt = (value: number): string => formatter.render(value)
  const points = metric.data_points
  if (!points || points.length === 0) {
    return { min: 'n/a', avg: 'n/a', max: 'n/a', last: 'n/a' }
  }
  let min = Infinity
  let max = -Infinity
  let sum = 0
  let count = 0
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
    }
  }
  const last = points[points.length - 1]!
  return {
    min: isFinite(min) ? fmt(min) : 'n/a',
    avg: count > 0 ? fmt(sum / count) : 'n/a',
    max: isFinite(max) ? fmt(max) : 'n/a',
    last: last !== null && isFinite(last) ? fmt(last) : 'n/a'
  }
}

/** The line's value rendered with its own unit, as the metric stats are. */
export function horizontalLineValue(line: HorizontalLine): string {
  const { formatter } = userSpecificUnit(line.unit, 'celsius')
  return formatter.render(line.value)
}

export function metricsInGraphTopToBottomOrder(metrics: Metric[]): Metric[] {
  return consecutiveStackGroups(metrics).flatMap(topmostSeriesFirst)
}

function consecutiveStackGroups(metrics: Metric[]): Metric[][] {
  const groups: Metric[][] = []
  for (const metric of metrics) {
    const currentGroup = groups[groups.length - 1]
    if (currentGroup !== undefined && belongsToSameStack(currentGroup, metric)) {
      currentGroup.push(metric)
    } else {
      groups.push([metric])
    }
  }
  return groups
}

function belongsToSameStack(group: Metric[], metric: Metric): boolean {
  return metric.render.stack !== null && metric.render.stack === group[0]!.render.stack
}

function topmostSeriesFirst(group: Metric[]): Metric[] {
  const stackedSeriesDrawBottomUp = group[0]!.render.stack !== null
  return stackedSeriesDrawBottomUp ? [...group].reverse() : group
}

export function withNameToggled(hiddenNames: string[], name: string): string[] {
  if (hiddenNames.includes(name)) {
    return hiddenNames.filter((hiddenName) => hiddenName !== name)
  }
  return [...hiddenNames, name]
}
