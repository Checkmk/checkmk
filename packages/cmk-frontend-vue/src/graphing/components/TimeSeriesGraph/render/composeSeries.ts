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
import { type DomainBucket, computeYDomain } from '../axes/valueAxis'
import { downsampleToColumns, edgeNeighbours, edgeSample, m4 } from '../decimation/decimate'
import type { M4Bucket, M4Cache } from '../decimation/types'
import type { Metric, ShadedRegion, TimeRange } from '../types'
import { invertBucket, keptSamples } from './bucket'
import { connectorPolylines } from './line'
import { type TimeValuePoint, clampedValueAt } from './polyline'
import { type AreaSeries, type StackedSeries, bandOutlines, computeStackedSeries } from './stacked'

export interface ComposedSeries {
  bucketsOnPlot: M4Cache[]
  paddedBuckets: M4Cache[]
  stacks: StackedSeries[]
  stacksOnPlot: StackedSeries[]
  valuesDrawnOnPlot: number[][]
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
}): ComposedSeries {
  const { metrics, cache, visibleTimeRange, columnCount } = options

  const bucketsOnPlot = cache.map((metricCache) => {
    const columns = downsampleToColumns(metricCache, visibleTimeRange, columnCount)
    const sampleOnTheRightEdge = edgeSample(metricCache, visibleTimeRange[1])
    return sampleOnTheRightEdge === undefined ? columns : [...columns, sampleOnTheRightEdge]
  })

  // Inverse mirrors a metric below the baseline; stacking then resolves cumulative bands.
  const paddedBuckets = cache.map((metricCache, i) => {
    const [before, after] = edgeNeighbours(metricCache, visibleTimeRange)
    const padded = [before, ...bucketsOnPlot[i]!, after]
    return metrics[i]!.render.inverse ? padded.map((bucket) => invertBucket(bucket)) : padded
  })

  const stacks = computeStackedSeries(metrics, paddedBuckets)
  return {
    bucketsOnPlot,
    paddedBuckets,
    stacks,
    stacksOnPlot: stacks.map(onPlotSeries),
    valuesDrawnOnPlot: stacks.map((series, i) =>
      series.kind === 'area-stacked'
        ? bandValuesDrawnOn(visibleTimeRange, series)
        : lineValuesDrawnOn(visibleTimeRange, paddedBuckets[i]!)
    )
  }
}

function isWithin([start, end]: [number, number], time: number): boolean {
  return start <= time && time <= end
}

function spans(polyline: TimeValuePoint[], time: number): boolean {
  const first = polyline[0]
  const last = polyline[polyline.length - 1]
  return first !== undefined && last !== undefined && isWithin([first.time, last.time], time)
}

function valuesDrawnOn(
  plotTimeRange: [number, number],
  polylines: TimeValuePoint[][],
  vertices: TimeValuePoint[]
): number[] {
  const verticesOnPlot = vertices.filter((vertex) => isWithin(plotTimeRange, vertex.time))
  const crossingsOfThePlotEdges = plotTimeRange.flatMap((plotEdge) => {
    const crossing = polylines.find((polyline) => spans(polyline, plotEdge))
    return crossing === undefined ? [] : [clampedValueAt(crossing, plotEdge)]
  })
  return [...verticesOnPlot.map((vertex) => vertex.value), ...crossingsOfThePlotEdges]
}

function lineValuesDrawnOn(plotTimeRange: [number, number], buckets: M4Bucket[]): number[] {
  return valuesDrawnOn(plotTimeRange, connectorPolylines(buckets), buckets.flatMap(keptSamples))
}

function bandValuesDrawnOn(plotTimeRange: [number, number], series: AreaSeries): number[] {
  const outlines = bandOutlines(series)
  return (['lower', 'upper'] as const).flatMap((side) => {
    const edge = outlines.map((outline) =>
      outline.map((vertex) => ({ time: vertex.time, value: vertex[side] }))
    )
    return valuesDrawnOn(plotTimeRange, edge, edge.flat())
  })
}

function onPlotSeries(series: StackedSeries): StackedSeries {
  return series.kind === 'area-stacked'
    ? { kind: series.kind, columns: withoutOffPlotNeighbours(series.columns) }
    : series
}

export function hasMirroredMetric(metrics: Metric[]): boolean {
  return metrics.some((metric) => metric.render.inverse)
}

function mixesMirroredAndUnmirrored(metrics: Metric[]): boolean {
  return hasMirroredMetric(metrics) && metrics.some((metric) => !metric.render.inverse)
}

function asDomainBucket(value: number): DomainBucket {
  return { gap: false, minValue: value, maxValue: value }
}

function regionBoundBuckets(regions: ShadedRegion[]): DomainBucket[][] {
  return regions.flatMap((region) =>
    [region.data_points.lower, region.data_points.upper].flatMap((bound) =>
      bound === null || bound === undefined
        ? []
        : [
            bound.flatMap((value) =>
              value === null ? [] : [{ gap: false, minValue: value, maxValue: value }]
            )
          ]
    )
  )
}

/**
 * The value extent the y-axis must cover. Line metrics contribute their drawn extremes; stacked
 * metrics their cumulative band extents.
 */
export function composedValueDomain(
  metrics: Metric[],
  composed: ComposedSeries,
  regions: ShadedRegion[] = []
): [number, number] {
  const domainBuckets = metrics.flatMap((metric, i) => {
    if (metric.render.hidden) {
      return []
    }
    return [composed.valuesDrawnOnPlot[i]!.map(asDomainBucket)]
  })
  return computeYDomain([...domainBuckets, ...regionBoundBuckets(regions)], {
    symmetric: mixesMirroredAndUnmirrored(metrics)
  })
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
