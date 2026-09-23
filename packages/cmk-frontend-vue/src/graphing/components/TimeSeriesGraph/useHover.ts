/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { bisector } from 'd3-array'
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { type Ref, onBeforeUnmount, ref } from 'vue'

import type { ConsolidationFn } from '../consolidation'
import { attributesOf } from '../metricAttributes'
import { orderMetricsTopToBottom } from '../metricOrder'
import type { M4Bucket, M4Cache } from './decimation/types'
import { type HoverSample, type HoverState, metricHitDistance } from './interaction/hover'
import { consolidatedSampleTime, keptSamples, selectConsolidatedValue } from './render/bucket'
import { type TimeValuePoint, clampedValueAt } from './render/polyline'
import type { StackedColumn, StackedSeries } from './render/stacked'
import type { Metric, UnitFormat } from './types'
import { valueRenderer } from './valueRenderer'

const HOVER_CLEAR_DELAY_MS = 150

const CLOSEST_METRIC_REACH_PX = 24

const bucketCentre = (bucket: M4Bucket): number => (bucket.startTime + bucket.endTime) / 2

// Gaps hold no drawn point; their column centre keeps the sequence ordered for the bisector and
// resolves a cursor over a gap to the gap itself.
function drawnTime(bucket: M4Bucket, consolidation: ConsolidationFn): number {
  return bucket.gap ? bucketCentre(bucket) : consolidatedSampleTime(bucket, consolidation)
}

const bisectorFor = (consolidation: ConsolidationFn) =>
  bisector<M4Bucket, number>((bucket) => drawnTime(bucket, consolidation)).center
const bisectDrawnPoint: Record<ConsolidationFn, ReturnType<typeof bisectorFor>> = {
  min: bisectorFor('min'),
  max: bisectorFor('max'),
  avg: bisectorFor('avg')
}
const bisectColumnStart = bisector<M4Bucket, number>((bucket) => bucket.startTime)

function keptSampleAt(bucket: M4Bucket | undefined, time: number): TimeValuePoint | undefined {
  return bucket === undefined ? undefined : keptSamples(bucket).find((kept) => kept.time === time)
}

interface DrawnEdge {
  lower: number
  upper: number
}

function edgeAt(column: StackedColumn, time: number): DrawnEdge {
  const lowerEdge = column.vertices.map((vertex) => ({ time: vertex.time, value: vertex.lower }))
  const upperEdge = column.vertices.map((vertex) => ({ time: vertex.time, value: vertex.upper }))
  return { lower: clampedValueAt(lowerEdge, time), upper: clampedValueAt(upperEdge, time) }
}

function drawnEdge(
  series: StackedSeries,
  columnIndex: number,
  drawnValue: number,
  time: number
): DrawnEdge | null {
  if (series.kind === 'line') {
    return { lower: drawnValue, upper: drawnValue }
  }
  const column = series.columns[columnIndex]
  return column === undefined || column.gap ? null : edgeAt(column, time)
}

// The hover reads the buckets as fetched, while an inverse metric is drawn mirrored: what the
// renderer drew as the maximum is the minimum of these buckets. `invertBucket` swaps exactly the
// min/max fields, so reading the mirrored curve is a matter of flipping the consolidation.
function asDrawn(consolidation: ConsolidationFn, inverse: boolean): ConsolidationFn {
  if (!inverse) {
    return consolidation
  }
  switch (consolidation) {
    case 'min':
      return 'max'
    case 'max':
      return 'min'
    case 'avg':
      return 'avg'
  }
}

const coversTime = (buckets: M4Cache, time: number): boolean =>
  buckets.length > 0 &&
  time >= buckets[0]!.startTime &&
  time <= buckets[buckets.length - 1]!.endTime

interface Reading {
  value: number
  time: number
  edge: DrawnEdge
}

function indexOfClosest(distances: Array<number | null>): number {
  let closestIdx = -1
  let closestDistance = CLOSEST_METRIC_REACH_PX
  distances.forEach((distance, i) => {
    if (distance !== null && distance <= closestDistance) {
      closestDistance = distance
      closestIdx = i
    }
  })
  return closestIdx
}

export interface HoverOptions {
  metrics: () => Metric[]
  consolidation: () => ConsolidationFn
  valueResolution: () => number | null
  axisUnit: () => UnitFormat | null
  plotWidth: Ref<number>
  plotHeight: Ref<number>
  xScale: ScaleTime<number, number>
  yScale: ScaleLinear<number, number>
}

export interface HoverPoint {
  x: number
  y: number
  clientX: number
  clientY: number
}

export function useHover(options: HoverOptions) {
  const hoverState: Ref<HoverState | null> = ref(null)

  let drawnBuckets: M4Cache[] = []
  let drawnStacks: StackedSeries[] = []
  function recordDrawnGeometry(buckets: M4Cache[], stacks: StackedSeries[]): void {
    drawnBuckets = buckets
    drawnStacks = stacks
  }

  function toReading(
    metric: Metric,
    metricIndex: number,
    columnIndex: number,
    value: number,
    time: number
  ): Reading | null {
    if (!Number.isFinite(value)) {
      return null
    }
    const series: StackedSeries = drawnStacks[metricIndex] ?? { kind: 'line' }
    const edge = drawnEdge(series, columnIndex, metric.render.inverse ? -value : value, time)
    return edge === null ? null : { value, time, edge }
  }

  function readingAtCursor(
    metric: Metric,
    metricIndex: number,
    cursorTime: number
  ): Reading | null {
    const buckets = drawnBuckets[metricIndex] ?? []
    const isStackReference = metric.render.hidden
    if (isStackReference || !coversTime(buckets, cursorTime)) {
      return null
    }
    const consolidation = asDrawn(options.consolidation(), metric.render.inverse)
    const columnIndex = Math.min(
      bisectDrawnPoint[consolidation](buckets, cursorTime),
      buckets.length - 1
    )
    const bucket = buckets[columnIndex]!
    return toReading(
      metric,
      metricIndex,
      columnIndex,
      selectConsolidatedValue(bucket, consolidation),
      drawnTime(bucket, consolidation)
    )
  }

  function drawnReadingAtTime(metric: Metric, metricIndex: number, time: number): Reading | null {
    const buckets = drawnBuckets[metricIndex] ?? []
    const columnOfTime = bisectColumnStart.right(buckets, time) - 1
    const columnStraddledInto = columnOfTime + 1
    for (const columnIndex of [columnOfTime, columnStraddledInto]) {
      const sample = keptSampleAt(buckets[columnIndex], time)
      if (sample !== undefined) {
        return toReading(metric, metricIndex, columnIndex, sample.value, time)
      }
    }
    return null
  }

  function hitDistance(cursorY: number, reading: Reading): number {
    return metricHitDistance(
      cursorY,
      options.yScale(reading.edge.upper),
      options.yScale(reading.edge.lower)
    )
  }

  function toSample(metric: Metric, reading: Reading | null, isClosest: boolean): HoverSample {
    const sampleBase = {
      metricName: metric.metadata.name,
      label: metric.metadata.title,
      color: metric.metadata.color,
      attributes: attributesOf(metric),
      isClosest
    }
    if (reading === null) {
      return { ...sampleBase, formattedValue: 'n/a', drawnPoint: null, snapTime: null }
    }
    const renderValue = valueRenderer(
      options.axisUnit() ?? metric.metadata.unit,
      options.valueResolution()
    )
    return {
      ...sampleBase,
      formattedValue: renderValue(reading.value),
      drawnPoint: {
        x: options.xScale(new Date(reading.time * 1000)),
        y: options.yScale(reading.edge.upper)
      },
      snapTime: reading.time
    }
  }

  function computeHover(point: HoverPoint): HoverState | null {
    // An empty frame still has axes to hover, but nothing to report over them.
    if (options.metrics().length === 0) {
      return null
    }
    const { x: cursorX, y: cursorY } = point
    if (
      cursorX < 0 ||
      cursorX > options.plotWidth.value ||
      cursorY < 0 ||
      cursorY > options.plotHeight.value
    ) {
      return null
    }
    const cursorTime = (options.xScale.invert(cursorX) as Date).getTime() / 1000

    const metricsList = options.metrics()
    const readingsAtCursor = metricsList.map((metric, i) => readingAtCursor(metric, i, cursorTime))
    const closestIdx = indexOfClosest(
      readingsAtCursor.map((reading) => (reading === null ? null : hitDistance(cursorY, reading)))
    )

    const indexOfMetric = new Map(metricsList.map((metric, i) => [metric, i]))
    const indicesInLegendOrder = orderMetricsTopToBottom(metricsList)
      .filter((metric) => !metric.render.hidden)
      .map((metric) => indexOfMetric.get(metric)!)

    const hoverTime =
      readingsAtCursor[closestIdx]?.time ??
      indicesInLegendOrder.map((i) => readingsAtCursor[i]!).find((reading) => reading !== null)
        ?.time ??
      cursorTime
    const readings = readingsAtCursor.map((cursorReading, i) =>
      cursorReading === null || cursorReading.time === hoverTime
        ? cursorReading
        : (drawnReadingAtTime(metricsList[i]!, i, hoverTime) ?? cursorReading)
    )

    return {
      cursorX,
      cursorY,
      clientX: point.clientX,
      clientY: point.clientY,
      snapX: options.xScale(new Date(hoverTime * 1000)),
      snapTime: hoverTime,
      samples: indicesInLegendOrder.map((i) =>
        toSample(metricsList[i]!, readings[i]!, i === closestIdx)
      )
    }
  }

  let hoverClearTimer: ReturnType<typeof setTimeout> | null = null
  function cancelPendingHoverClear(): void {
    if (hoverClearTimer !== null) {
      clearTimeout(hoverClearTimer)
      hoverClearTimer = null
    }
  }
  function clearHoverAfterDelay(): void {
    cancelPendingHoverClear()
    hoverClearTimer = setTimeout(() => {
      hoverState.value = null
      hoverClearTimer = null
    }, HOVER_CLEAR_DELAY_MS)
  }
  function clearHover(): void {
    cancelPendingHoverClear()
    hoverState.value = null
  }

  function moveHoverTo(point: HoverPoint | null): void {
    cancelPendingHoverClear()
    if (!point) {
      return
    }
    hoverState.value = computeHover(point)
  }

  onBeforeUnmount(cancelPendingHoverClear)

  return {
    hoverState,
    recordDrawnGeometry,
    moveHoverTo,
    clearHover,
    cancelPendingHoverClear,
    clearHoverAfterDelay
  }
}
