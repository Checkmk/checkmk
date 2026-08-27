/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// The steps between a fetch's samples and the arguments `drawData` paints from. The plot and the
// brush strip draw different fetches over different extents, but the composition is the same, so
// it lives here rather than in either of them: a metric's kind, its stacking base and the value
// extent it forces are the render contract, and two implementations of that is what let the strip
// drift from the plot it summarises.
import type { ConsolidationFn } from '../../consolidation'
import { computeYDomain } from '../axes/valueAxis'
import { downsampleToColumns, edgeNeighbours, edgeSample, m4 } from '../decimation/decimate'
import type { M4Cache } from '../decimation/types'
import type { Metric, TimeRange } from '../types'
import { invertBucket } from './bucket'
import { type StackedSeries, computeStackedSeries } from './stacked'

export interface ComposedSeries {
  bucketsOnPlot: M4Cache[]
  paddedBuckets: M4Cache[]
  stacks: StackedSeries[]
}

/** Strips the flanking off-plot neighbours `composeSeries` pads with. */
export function withoutOffPlotNeighbours<T>(items: T[]): T[] {
  return items.slice(1, -1)
}

export function composeSeries(options: {
  metrics: Metric[]
  cache: M4Cache[]
  visibleTimeRange: [number, number]
  columnCount: number
  consolidation: ConsolidationFn
}): ComposedSeries {
  const { metrics, cache, visibleTimeRange, columnCount, consolidation } = options

  const bucketsOnPlot = cache.map((metricCache) => [
    ...downsampleToColumns(metricCache, visibleTimeRange, columnCount),
    edgeSample(metricCache, visibleTimeRange[1])
  ])

  // Inverse mirrors a metric below the baseline; stacking then resolves cumulative bands.
  const paddedBuckets = cache.map((metricCache, i) => {
    const [before, after] = edgeNeighbours(metricCache, visibleTimeRange)
    const padded = [before, ...bucketsOnPlot[i]!, after]
    return metrics[i]!.render.inverse ? padded.map((bucket) => invertBucket(bucket)) : padded
  })

  return {
    bucketsOnPlot,
    paddedBuckets,
    stacks: computeStackedSeries(metrics, paddedBuckets, consolidation)
  }
}

/**
 * The value extent the y-axis must cover. Line metrics contribute their drawn extremes; stacked
 * metrics their cumulative band extents. Forced symmetric around zero when any metric is inverse.
 */
export function composedValueDomain(metrics: Metric[], composed: ComposedSeries): [number, number] {
  const domainBuckets = metrics.map((_, i) =>
    composed.stacks[i]!.kind === 'area-stacked'
      ? withoutOffPlotNeighbours(composed.stacks[i]!.bands).map((band) => ({
          gap: band.gap,
          minValue: Math.min(band.lower, band.upper),
          maxValue: Math.max(band.lower, band.upper)
        }))
      : withoutOffPlotNeighbours(composed.paddedBuckets[i]!)
  )
  const anyInverse = metrics.some((metric) => metric.render.inverse)
  return computeYDomain(domainBuckets, { symmetric: anyInverse })
}

export interface M4CacheStore {
  /** Recomputes only when the metrics array or the range they were decimated over changes. */
  ensure: (metrics: Metric[], dataTimeRange: TimeRange) => M4Cache[]
}

export function createM4CacheStore(bucketCount: number): M4CacheStore {
  let cache: M4Cache[] = []
  let cachedMetrics: Metric[] | null = null
  let cachedTimeRange: TimeRange | null = null

  return {
    ensure(metrics, dataTimeRange) {
      if (cachedMetrics !== metrics || cachedTimeRange !== dataTimeRange) {
        cachedMetrics = metrics
        cachedTimeRange = dataTimeRange
        cache = metrics.map((metric) => m4(metric.data_points, dataTimeRange, bucketCount))
      }
      return cache
    }
  }
}
