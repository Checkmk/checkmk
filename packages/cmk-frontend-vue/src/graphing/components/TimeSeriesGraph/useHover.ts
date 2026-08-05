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
import type { M4Bucket, M4Cache } from './decimation/types'
import { type HoverSample, type HoverState, metricHitDistance } from './interaction/hover'
import { bucketAnchorTime, selectConsolidatedValue } from './render/bucket'
import type { StackedSeries } from './render/stacked'
import type { Metric } from './types'

const HOVER_CLEAR_DELAY_MS = 150

const CLOSEST_METRIC_REACH_PX = 24

const bucketCentre = (bucket: M4Bucket): number => (bucket.startTime + bucket.endTime) / 2

// Hovering resolves to the point the renderer actually drew, so the focus dots sit on the curve
// instead of floating between two of its vertices: whenever a sample is wider than a column, the
// columns it covers all carry that sample's value but only its anchor is a point on the curve.
// Gaps hold no drawn point; their column centre keeps the sequence ordered for the bisector and
// makes a cursor over a gap resolve to that gap rather than to a sample beyond it.
const drawnTime = (bucket: M4Bucket): number =>
  bucket.gap ? bucketCentre(bucket) : bucketAnchorTime(bucket)
const bisectDrawnPoint = bisector<M4Bucket, number>(drawnTime).center

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
      const filled = drawnStacks[i]?.kind === 'area-stacked'
      const sampleBase = {
        metricName: metric.metadata.name,
        label: metric.metadata.title,
        color: metric.metadata.color,
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
      const bucketIdx = Math.min(bisectDrawnPoint(buckets, cursorTime), buckets.length - 1)
      const bucket = buckets[bucketIdx]!
      const value = selectConsolidatedValue(bucket, options.consolidation())
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
        snapTime: bucketAnchorTime(bucket)
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
