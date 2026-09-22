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
import { consolidatedSampleTime, selectConsolidatedValue } from './render/bucket'
import { valueAt } from './render/polyline'
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

interface DrawnEdge {
  lower: number
  upper: number
}

function edgeAt(column: StackedColumn, time: number): DrawnEdge {
  const lowerEdge = column.vertices.map((vertex) => ({ time: vertex.time, value: vertex.lower }))
  const upperEdge = column.vertices.map((vertex) => ({ time: vertex.time, value: vertex.upper }))
  return { lower: valueAt(lowerEdge, time), upper: valueAt(upperEdge, time) }
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

    const hitDistances: Array<number | null> = []

    const metricsList = options.metrics()
    const samples: HoverSample[] = metricsList.map((metric, i) => {
      const buckets = drawnBuckets[i] ?? []
      const series: StackedSeries = drawnStacks[i] ?? { kind: 'line' }
      const consolidation = asDrawn(options.consolidation(), metric.render.inverse)
      const sampleBase = {
        metricName: metric.metadata.name,
        label: metric.metadata.title,
        color: metric.metadata.color,
        attributes: attributesOf(metric),
        isClosest: false
      }
      const sampleWithoutValue = {
        ...sampleBase,
        formattedValue: 'n/a',
        pixelY: null,
        snapTime: null
      }
      // Hidden metrics (stack references) are structural: no tooltip row, never "closest".
      if (metric.render.hidden || !coversTime(buckets, cursorTime)) {
        hitDistances.push(null)
        return sampleWithoutValue
      }
      const bucketIdx = Math.min(
        bisectDrawnPoint[consolidation](buckets, cursorTime),
        buckets.length - 1
      )
      const bucket = buckets[bucketIdx]!
      const value = selectConsolidatedValue(bucket, consolidation)
      const time = drawnTime(bucket, consolidation)
      const drawnValue = metric.render.inverse ? -value : value
      const edge = Number.isFinite(value) ? drawnEdge(series, bucketIdx, drawnValue, time) : null
      if (edge === null) {
        hitDistances.push(null)
        return sampleWithoutValue
      }
      const drawnTopPixel = options.yScale(edge.upper)
      const drawnBottomPixel = options.yScale(edge.lower)
      hitDistances.push(metricHitDistance(cursorY, drawnTopPixel, drawnBottomPixel))
      const renderValue = valueRenderer(
        options.axisUnit() ?? metric.metadata.unit,
        options.valueResolution()
      )
      return {
        ...sampleBase,
        formattedValue: renderValue(value),
        pixelY: drawnTopPixel,
        snapTime: time
      }
    })

    let closestIdx = -1
    let closestDistance = CLOSEST_METRIC_REACH_PX
    for (let i = 0; i < hitDistances.length; i++) {
      const distance = hitDistances[i]
      if (distance === null || distance === undefined) {
        continue
      }
      if (distance <= closestDistance) {
        closestDistance = distance
        closestIdx = i
      }
    }
    const closestSample = samples[closestIdx]
    if (closestSample) {
      closestSample.isClosest = true
    }

    // Listed as the legend lists them, topmost series first; the placeholder samples of
    // hidden metrics drop out. Index alignment with hitDistances is no longer needed.
    const sampleOfMetric = new Map(metricsList.map((metric, i) => [metric, samples[i]!]))
    const visibleSamples = orderMetricsTopToBottom(metricsList)
      .filter((metric) => !metric.render.hidden)
      .map((metric) => sampleOfMetric.get(metric)!)
    const snapSample = closestSample ?? visibleSamples.find((sample) => sample.snapTime !== null)
    const snapTime = snapSample?.snapTime ?? cursorTime
    const snapX = options.xScale(new Date(snapTime * 1000))

    return {
      cursorX,
      cursorY,
      clientX: point.clientX,
      clientY: point.clientY,
      snapX,
      snapTime,
      samples: visibleSamples
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
