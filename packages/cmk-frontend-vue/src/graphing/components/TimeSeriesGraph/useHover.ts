/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { bisector } from 'd3-array'
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { type Ref, onBeforeUnmount, ref } from 'vue'

import type { ConsolidationFn } from '../consolidation'
import { attributesOf } from '../metricAttributes'
import type { M4Bucket, M4Cache } from './decimation/types'
import { type HoverSample, type HoverState, metricHitDistance } from './interaction/hover'
import { bucketAnchorTime, consolidatedSampleTime, selectConsolidatedValue } from './render/bucket'
import type { StackedSeries, StackedSeriesKind } from './render/stacked'
import type { Metric } from './types'

const HOVER_CLEAR_DELAY_MS = 150

const CLOSEST_METRIC_REACH_PX = 24

const bucketCentre = (bucket: M4Bucket): number => (bucket.startTime + bucket.endTime) / 2

// The focus dot sits on what the renderer drew, which differs by kind: a line runs through its
// samples, so min/max report the time they were sampled at, while an avg is no sample and keeps
// the anchor; a stacked band is drawn at the anchor throughout. Gaps hold no drawn point, so
// their column centre keeps the sequence ordered for the bisector and resolves a cursor over a
// gap to the gap itself.
function drawnTime(
  bucket: M4Bucket,
  kind: StackedSeriesKind,
  consolidation: ConsolidationFn
): number {
  if (bucket.gap) {
    return bucketCentre(bucket)
  }
  return kind === 'area-stacked'
    ? bucketAnchorTime(bucket)
    : consolidatedSampleTime(bucket, consolidation)
}

const bisectorFor = (kind: StackedSeriesKind, consolidation: ConsolidationFn) =>
  bisector<M4Bucket, number>((bucket) => drawnTime(bucket, kind, consolidation)).center
const bisectDrawnPoint: Record<
  StackedSeriesKind,
  Record<ConsolidationFn, ReturnType<typeof bisectorFor>>
> = {
  line: {
    min: bisectorFor('line', 'min'),
    max: bisectorFor('line', 'max'),
    avg: bisectorFor('line', 'avg')
  },
  'area-stacked': {
    min: bisectorFor('area-stacked', 'min'),
    max: bisectorFor('area-stacked', 'max'),
    avg: bisectorFor('area-stacked', 'avg')
  }
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
      const bands = drawnStacks[i]?.bands ?? []
      const kind: StackedSeriesKind = drawnStacks[i]?.kind ?? 'line'
      const consolidation = asDrawn(options.consolidation(), metric.render.inverse)
      const filled = kind === 'area-stacked'
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
        bisectDrawnPoint[kind][consolidation](buckets, cursorTime),
        buckets.length - 1
      )
      const bucket = buckets[bucketIdx]!
      const value = selectConsolidatedValue(bucket, consolidation)
      const band = bands[bucketIdx]
      if (!Number.isFinite(value) || !band) {
        hitDistances.push(null)
        return sampleWithoutValue
      }
      const drawnTopPixel = options.yScale(band.upper)
      const drawnBottomPixel = options.yScale(band.lower)
      hitDistances.push(metricHitDistance(cursorY, drawnTopPixel, drawnBottomPixel, filled))
      const { formatter } = userSpecificUnit(metric.metadata.unit, 'celsius')
      return {
        ...sampleBase,
        formattedValue: formatter.render(value),
        pixelY: drawnTopPixel,
        snapTime: drawnTime(bucket, kind, consolidation)
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

    // Drop the placeholder samples of hidden metrics; index alignment with hitDistances
    // is no longer needed past this point.
    const visibleSamples = samples.filter((_, i) => !metricsList[i]!.render.hidden)
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
