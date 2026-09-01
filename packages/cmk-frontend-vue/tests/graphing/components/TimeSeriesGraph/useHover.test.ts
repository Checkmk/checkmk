/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { scaleLinear, scaleTime } from 'd3-scale'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import { downsampleToColumns, m4 } from '@/graphing/components/TimeSeriesGraph/decimation/decimate'
import { invertBucket } from '@/graphing/components/TimeSeriesGraph/render/bucket'
import { computeStackedSeries } from '@/graphing/components/TimeSeriesGraph/render/stacked'
import { useHover } from '@/graphing/components/TimeSeriesGraph/useHover'
import type { ConsolidationFn } from '@/graphing/components/consolidation'

const UNIT: Metric['metadata']['unit'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const TIME_RANGE = { start: 0, end: 100, step: 10 }
const PLOT_WIDTH = 100
const PLOT_HEIGHT = 100

function makeLineMetric(name: string, dataPoints: (number | null)[]): Metric {
  return {
    metadata: { name, title: name, unit: UNIT, color: '#ff0000' },
    render: { stack: null, inverse: false, hidden: false },
    data_points: dataPoints
  }
}

function makeInverseLineMetric(name: string, dataPoints: (number | null)[]): Metric {
  const metric = makeLineMetric(name, dataPoints)
  return { ...metric, render: { ...metric.render, inverse: true } }
}

function constantPoints(value: number | null): (number | null)[] {
  return Array.from({ length: 11 }, () => value)
}

function pointsValuedAtTheirOwnTimestamp(): (number | null)[] {
  return Array.from({ length: 10 }, (_, index) => (index + 1) * 10)
}

const PLOT_CLIENT_LEFT = 200
const PLOT_CLIENT_TOP = 300

function pointAt(x: number, y: number): { x: number; y: number; clientX: number; clientY: number } {
  return { x, y, clientX: PLOT_CLIENT_LEFT + x, clientY: PLOT_CLIENT_TOP + y }
}

interface HoverOverrides {
  consolidation?: ConsolidationFn
  plotWidth?: number
  /** Widen to cover the mirrored half of the plot when a metric is inverse. */
  valueDomain?: [number, number]
}

function mountHover(
  metrics: Metric[],
  dataRange = TIME_RANGE,
  overrides: HoverOverrides = {}
): ReturnType<typeof useHover> {
  const consolidation = overrides.consolidation ?? 'avg'
  const plotWidth = overrides.plotWidth ?? PLOT_WIDTH
  const xScale = scaleTime()
    .domain([new Date(TIME_RANGE.start * 1000), new Date(TIME_RANGE.end * 1000)])
    .range([0, plotWidth])
  const yScale = scaleLinear()
    .domain(overrides.valueDomain ?? [0, 100])
    .range([PLOT_HEIGHT, 0])
  let api!: ReturnType<typeof useHover>
  const harness = defineComponent({
    setup() {
      api = useHover({
        metrics: () => metrics,
        consolidation: () => consolidation,
        plotWidth: ref(plotWidth),
        plotHeight: ref(PLOT_HEIGHT),
        xScale,
        yScale
      })
      return () => h('div')
    }
  })
  render(harness)
  // One column per plot pixel, the way the renderer composes them.
  const buckets = metrics.map((metric) =>
    downsampleToColumns(
      m4(metric.data_points, dataRange, 4000),
      [dataRange.start, dataRange.end],
      plotWidth
    )
  )
  const drawnBuckets = buckets.map((metricBuckets, i) =>
    metrics[i]!.render.inverse ? metricBuckets.map(invertBucket) : metricBuckets
  )
  api.recordDrawnGeometry(buckets, computeStackedSeries(metrics, drawnBuckets, consolidation))
  return api
}

describe('useHover — hit-test', () => {
  test('flags the metric drawn nearest the cursor as closest', () => {
    const hover = mountHover([
      makeLineMetric('low', constantPoints(10)),
      makeLineMetric('high', constantPoints(90))
    ])

    hover.moveHoverTo(pointAt(50, 85))

    const samples = hover.hoverState.value!.samples
    expect(samples.map((sample) => [sample.metricName, sample.isClosest])).toEqual([
      ['low', true],
      ['high', false]
    ])
  })

  test('carries the cursor position and snaps the crosshair near it', () => {
    const hover = mountHover([makeLineMetric('low', constantPoints(10))])

    hover.moveHoverTo(pointAt(50, 85))

    const state = hover.hoverState.value!
    expect(state.cursorX).toBe(50)
    expect(state.cursorY).toBe(85)
    expect(state.clientX).toBe(PLOT_CLIENT_LEFT + 50)
    expect(state.clientY).toBe(PLOT_CLIENT_TOP + 85)
    expect(Math.abs(state.snapX - 50)).toBeLessThanOrEqual(1)
  })

  test('a metric without data points gets an n/a sample and is never closest', () => {
    const hover = mountHover([
      makeLineMetric('empty', constantPoints(null)),
      makeLineMetric('high', constantPoints(90))
    ])

    hover.moveHoverTo(pointAt(50, 15))

    const samples = hover.hoverState.value!.samples
    expect(samples[0]).toMatchObject({
      metricName: 'empty',
      formattedValue: 'n/a',
      pixelY: null,
      isClosest: false
    })
    expect(samples[1]!.isClosest).toBe(true)
  })

  test('a cursor out of reach of every curve singles none of them out', () => {
    const hover = mountHover([
      makeLineMetric('low', constantPoints(10)),
      makeLineMetric('high', constantPoints(90))
    ])

    // Halfway between the two curves, 40px from either.
    hover.moveHoverTo(pointAt(50, 50))

    const samples = hover.hoverState.value!.samples
    expect(samples.every((sample) => !sample.isClosest)).toBe(true)
  })

  test('a cursor out of reach still reports every metric it crosses', () => {
    const hover = mountHover([
      makeLineMetric('low', constantPoints(10)),
      makeLineMetric('high', constantPoints(90))
    ])

    hover.moveHoverTo(pointAt(50, 50))

    const samples = hover.hoverState.value!.samples
    expect(samples.map((sample) => sample.formattedValue)).toEqual(['10', '90'])
  })

  test('a plot with no metrics yields no hover state', () => {
    const hover = mountHover([])

    hover.moveHoverTo(pointAt(50, 85))

    expect(hover.hoverState.value).toBeNull()
  })

  test('a cursor outside the plot yields no hover state', () => {
    const hover = mountHover([makeLineMetric('low', constantPoints(10))])
    hover.moveHoverTo(pointAt(50, 85))

    hover.moveHoverTo(pointAt(-1, 50))

    expect(hover.hoverState.value).toBeNull()
  })

  test('a cursor past the data extent shows n/a samples snapped to the cursor', () => {
    const hover = mountHover([makeLineMetric('low', constantPoints(10))], {
      start: 0,
      end: 50,
      step: 10
    })

    hover.moveHoverTo(pointAt(80, 85))

    const state = hover.hoverState.value!
    expect(state.samples[0]).toMatchObject({
      metricName: 'low',
      formattedValue: 'n/a',
      pixelY: null,
      isClosest: false
    })
    expect(Math.abs(state.snapX - 80)).toBeLessThanOrEqual(1)
  })

  test('a column where no metric has a drawn sample keeps the crosshair at the cursor', () => {
    const hover = mountHover([makeLineMetric('empty', constantPoints(null))])

    hover.moveHoverTo(pointAt(50, 85))

    const state = hover.hoverState.value!
    expect(state.samples[0]).toMatchObject({ formattedValue: 'n/a', isClosest: false })
    expect(Math.abs(state.snapX - 50)).toBeLessThanOrEqual(1)
  })
})

describe('useHover — snapping to drawn points', () => {
  test('a cursor between two samples snaps back to the nearer one', () => {
    const hover = mountHover([makeLineMetric('sloped', pointsValuedAtTheirOwnTimestamp())])

    hover.moveHoverTo(pointAt(53, 50))

    const state = hover.hoverState.value!
    expect(state.snapTime).toBe(50)
    expect(state.snapX).toBe(50)
    expect(state.samples[0]).toMatchObject({ formattedValue: '50', pixelY: 50 })
  })

  test('a cursor past the midpoint between two samples snaps forward to the next one', () => {
    const hover = mountHover([makeLineMetric('sloped', pointsValuedAtTheirOwnTimestamp())])

    hover.moveHoverTo(pointAt(57, 50))

    const state = hover.hoverState.value!
    expect(state.snapTime).toBe(60)
    expect(state.snapX).toBe(60)
    expect(state.samples[0]).toMatchObject({ formattedValue: '60', pixelY: 40 })
  })

  // A plot width the sample step does not divide leaves one column per sample pair straddling
  // both of them: the value consolidated over such a column belongs to one of the two samples,
  // and reporting it at the midpoint between them would float the focus dot off the curve.
  test('a column straddling two samples reports one of them, never the midpoint', () => {
    const hover = mountHover(
      [makeLineMetric('sloped', pointsValuedAtTheirOwnTimestamp())],
      {
        start: 0,
        end: 100,
        step: 10
      },
      { consolidation: 'max', plotWidth: 97 }
    )

    for (let x = 0; x <= 97; x++) {
      hover.moveHoverTo(pointAt(x, 50))
      const state = hover.hoverState.value!
      const sample = state.samples[0]!
      if (sample.pixelY === null) {
        continue
      }
      // Every sample is valued at its own timestamp, so a reported point is only a point of
      // the curve when its value and the time it is reported at agree.
      expect(sample.formattedValue).toBe(String(state.snapTime))
    }
  })

  // An inverse metric is drawn mirrored, so the top of its curve is the bucket's minimum. The
  // hover reads the buckets as fetched, where that minimum is still the minimum.
  test('an inverse metric reports the sample its mirrored curve peaks at', () => {
    const hover = mountHover(
      [makeInverseLineMetric('mirrored', pointsValuedAtTheirOwnTimestamp())],
      { start: 0, end: 100, step: 10 },
      { consolidation: 'max', plotWidth: 97, valueDomain: [-100, 100] }
    )

    for (let x = 0; x <= 97; x++) {
      hover.moveHoverTo(pointAt(x, 50))
      const sample = hover.hoverState.value!.samples[0]!
      if (sample.pixelY === null) {
        continue
      }
      // Every sample is valued at its own timestamp, and the dot is drawn at the negated value.
      expect(sample.formattedValue).toBe(String(hover.hoverState.value!.snapTime))
      expect(sample.pixelY).toBeCloseTo((100 + Number(sample.formattedValue)) / 2)
    }
  })

  test('a cursor over a gap stays n/a instead of snapping to a neighbouring sample', () => {
    const gappedPoints = pointsValuedAtTheirOwnTimestamp()
    const indexOfSampleAtT50 = 4
    gappedPoints[indexOfSampleAtT50] = null
    const hover = mountHover([makeLineMetric('gapped', gappedPoints)])

    hover.moveHoverTo(pointAt(53, 50))

    expect(hover.hoverState.value!.samples[0]).toMatchObject({
      formattedValue: 'n/a',
      pixelY: null
    })
  })
})

describe('useHover — clearing', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  test('clearHover drops the state immediately', () => {
    const hover = mountHover([makeLineMetric('low', constantPoints(10))])
    hover.moveHoverTo(pointAt(50, 85))

    hover.clearHover()

    expect(hover.hoverState.value).toBeNull()
  })

  test('clearHoverAfterDelay drops the state only once the delay elapsed', () => {
    vi.useFakeTimers()
    const hover = mountHover([makeLineMetric('low', constantPoints(10))])
    hover.moveHoverTo(pointAt(50, 85))

    hover.clearHoverAfterDelay()

    expect(hover.hoverState.value).not.toBeNull()
    vi.advanceTimersByTime(150)
    expect(hover.hoverState.value).toBeNull()
  })

  test('cancelPendingHoverClear keeps the state alive past the delay', () => {
    vi.useFakeTimers()
    const hover = mountHover([makeLineMetric('low', constantPoints(10))])
    hover.moveHoverTo(pointAt(50, 85))
    hover.clearHoverAfterDelay()

    hover.cancelPendingHoverClear()

    vi.advanceTimersByTime(1000)
    expect(hover.hoverState.value).not.toBeNull()
  })

  test('moving the hover cancels a pending clear', () => {
    vi.useFakeTimers()
    const hover = mountHover([makeLineMetric('low', constantPoints(10))])
    hover.moveHoverTo(pointAt(50, 85))
    hover.clearHoverAfterDelay()

    hover.moveHoverTo(pointAt(60, 85))

    vi.advanceTimersByTime(1000)
    expect(hover.hoverState.value).not.toBeNull()
  })
})
