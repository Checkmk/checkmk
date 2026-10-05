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
import type { HoverState } from '@/graphing/components/TimeSeriesGraph/interaction/hover'
import { invertBucket } from '@/graphing/components/TimeSeriesGraph/render/bucket'
import { composeSeries } from '@/graphing/components/TimeSeriesGraph/render/composeSeries'
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
    metadata: { name, title: name, unit: UNIT, color: '#ff0000', attributes: [] },
    render: { shape: 'line', inverse: false, hidden: false },
    data_points: dataPoints
  }
}

function makeInverseLineMetric(name: string, dataPoints: (number | null)[]): Metric {
  const metric = makeLineMetric(name, dataPoints)
  return { ...metric, render: { ...metric.render, inverse: true } }
}

function makeStackedMetric(
  name: string,
  dataPoints: (number | null)[],
  stack: string,
  hidden = false
): Metric {
  const metric = makeLineMetric(name, dataPoints)
  return { ...metric, render: { shape: 'area', stack, inverse: false, hidden } }
}

function constantPoints(value: number | null): (number | null)[] {
  return Array.from({ length: 11 }, () => value)
}

function pointsValuedAtTheirOwnTimestamp(count = 10, step = TIME_RANGE.step): number[] {
  return Array.from({ length: count }, (_, index) => (index + 1) * step)
}

const PLOT_CLIENT_LEFT = 200
const PLOT_CLIENT_TOP = 300

function pointAt(x: number, y: number): { x: number; y: number; clientX: number; clientY: number } {
  return { x, y, clientX: PLOT_CLIENT_LEFT + x, clientY: PLOT_CLIENT_TOP + y }
}

function makeScales(plotWidth = PLOT_WIDTH, valueDomain: [number, number] = [0, 100]) {
  const xScale = scaleTime()
    .domain([new Date(TIME_RANGE.start * 1000), new Date(TIME_RANGE.end * 1000)])
    .range([0, plotWidth])
  const yScale = scaleLinear().domain(valueDomain).range([PLOT_HEIGHT, 0])
  return { xScale, yScale }
}

interface HoverOverrides {
  consolidation?: ConsolidationFn
  plotWidth?: number
  /** Widen to cover the mirrored half of the plot when a metric is inverse. */
  valueDomain?: [number, number]
  valueResolution?: number | null
  axisUnit?: Metric['metadata']['unit'] | null
}

function renderHover(
  metrics: Metric[],
  dataRange: typeof TIME_RANGE,
  scales: ReturnType<typeof makeScales>,
  overrides: HoverOverrides = {}
): ReturnType<typeof useHover> {
  let api!: ReturnType<typeof useHover>
  const harness = defineComponent({
    setup() {
      api = useHover({
        metrics: () => metrics,
        dataTimeRange: () => dataRange,
        consolidation: () => overrides.consolidation ?? 'avg',
        valueResolution: () => overrides.valueResolution ?? null,
        axisUnit: () => overrides.axisUnit ?? null,
        plotWidth: ref(overrides.plotWidth ?? PLOT_WIDTH),
        plotHeight: ref(PLOT_HEIGHT),
        xScale: scales.xScale,
        yScale: scales.yScale
      })
      return () => h('div')
    }
  })
  render(harness)
  return api
}

function mountHover(
  metrics: Metric[],
  dataRange = TIME_RANGE,
  overrides: HoverOverrides = {}
): ReturnType<typeof useHover> {
  const plotWidth = overrides.plotWidth ?? PLOT_WIDTH
  const api = renderHover(
    metrics,
    dataRange,
    makeScales(plotWidth, overrides.valueDomain),
    overrides
  )
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
  api.recordDrawnGeometry(buckets, computeStackedSeries(metrics, drawnBuckets))
  return api
}

function mountHoverOverWindow(
  metrics: Metric[],
  dataRange: typeof TIME_RANGE,
  plotWindow: [number, number]
): ReturnType<typeof useHover> {
  const xScale = scaleTime()
    .domain(plotWindow.map((time) => new Date(time * 1000)))
    .range([0, PLOT_WIDTH])
  const yScale = scaleLinear().domain([0, dataRange.end]).range([PLOT_HEIGHT, 0])
  const api = renderHover(metrics, dataRange, { xScale, yScale }, { consolidation: 'max' })
  const composed = composeSeries({
    metrics,
    cache: metrics.map((metric) => m4(metric.data_points, dataRange, 4000)),
    dataTimeRange: dataRange,
    visibleTimeRange: plotWindow,
    columnCount: PLOT_WIDTH,
    binEdges: null
  })
  api.recordDrawnGeometry(composed.bucketsOnPlot, composed.stacksOnPlot)
  return api
}

function hoverStatesAcrossPlotMiddle(
  hover: ReturnType<typeof useHover>,
  fromX: number,
  toX: number
): HoverState[] {
  const states: HoverState[] = []
  for (let x = fromX; x <= toX; x++) {
    hover.moveHoverTo(pointAt(x, PLOT_HEIGHT / 2))
    states.push(hover.hoverState.value!)
  }
  return states
}

function drawnPointsOf(states: HoverState[], metricName: string): Array<{ x: number; y: number }> {
  return states.flatMap((state) => {
    const { drawnPoint } = state.samples.find((sample) => sample.metricName === metricName)!
    return drawnPoint === null ? [] : [drawnPoint]
  })
}

describe('useHover — hit-test', () => {
  test('flags the metric drawn nearest the cursor as closest', () => {
    const hover = mountHover([
      makeLineMetric('low', constantPoints(10)),
      makeLineMetric('high', constantPoints(90))
    ])

    hover.moveHoverTo(pointAt(50, 85))

    const samples = hover.hoverState.value!.samples
    expect(samples.filter((sample) => sample.isClosest).map((sample) => sample.metricName)).toEqual(
      ['low']
    )
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
    expect(samples.find((sample) => sample.metricName === 'empty')).toMatchObject({
      formattedValue: 'n/a',
      drawnPoint: null,
      isClosest: false
    })
    expect(samples.find((sample) => sample.metricName === 'high')!.isClosest).toBe(true)
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
    expect(samples.map((sample) => sample.formattedValue).sort()).toEqual(['10', '90'])
  })

  test('tells apart two values one axis step apart', () => {
    const valueResolution = 0.005
    const hover = mountHover(
      [makeLineMetric('low', constantPoints(0.195)), makeLineMetric('high', constantPoints(0.2))],
      TIME_RANGE,
      { valueDomain: [0.19, 0.21], valueResolution }
    )

    hover.moveHoverTo(pointAt(50, 50))

    const valueByMetric = Object.fromEntries(
      hover.hoverState.value!.samples.map((sample) => [sample.metricName, sample.formattedValue])
    )
    expect(valueByMetric).toEqual({ low: '0.195', high: '0.2' })
  })

  test('falls back to the unit precision without an axis resolution', () => {
    const hover = mountHover([makeLineMetric('low', constantPoints(0.195))], TIME_RANGE, {
      valueDomain: [0.19, 0.21]
    })

    hover.moveHoverTo(pointAt(50, 50))

    const samples = hover.hoverState.value!.samples
    expect(samples.map((sample) => sample.formattedValue)).toEqual(['0.2'])
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
      drawnPoint: null,
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

describe('useHover — lines over areas', () => {
  // Usage fills pixels 20–100; the limit line runs through it at pixel 70.
  const lineInsideArea = () => [
    makeStackedMetric('usage', constantPoints(80), 's1'),
    makeLineMetric('limit', constantPoints(30))
  ]

  test('a cursor on a line drawn over an area singles out the line', () => {
    const hover = mountHover(lineInsideArea())

    hover.moveHoverTo(pointAt(50, 72))

    const closest = hover.hoverState.value!.samples.filter((sample) => sample.isClosest)
    expect(closest.map((sample) => sample.metricName)).toEqual(['limit'])
  })

  test('a cursor inside an area away from the line over it singles out the area', () => {
    const hover = mountHover(lineInsideArea())

    hover.moveHoverTo(pointAt(50, 40))

    const closest = hover.hoverState.value!.samples.filter((sample) => sample.isClosest)
    expect(closest.map((sample) => sample.metricName)).toEqual(['usage'])
  })

  test('of two lines next to the cursor the nearer one is singled out', () => {
    // Pixels 70 and 74: both close to the cursor, the first one closer.
    const hover = mountHover([
      makeLineMetric('nearer', constantPoints(30)),
      makeLineMetric('farther', constantPoints(26))
    ])

    hover.moveHoverTo(pointAt(50, 71))

    const closest = hover.hoverState.value!.samples.filter((sample) => sample.isClosest)
    expect(closest.map((sample) => sample.metricName)).toEqual(['nearer'])
  })
})

describe('useHover — snapping to drawn points', () => {
  test('a cursor between two samples snaps back to the nearer one', () => {
    const hover = mountHover([makeLineMetric('sloped', pointsValuedAtTheirOwnTimestamp())])

    hover.moveHoverTo(pointAt(53, 50))

    const state = hover.hoverState.value!
    expect(state.snapTime).toBe(50)
    expect(state.snapX).toBe(50)
    expect(state.samples[0]).toMatchObject({ formattedValue: '50', drawnPoint: { x: 50, y: 50 } })
  })

  test('a cursor past the midpoint between two samples snaps forward to the next one', () => {
    const hover = mountHover([makeLineMetric('sloped', pointsValuedAtTheirOwnTimestamp())])

    hover.moveHoverTo(pointAt(57, 50))

    const state = hover.hoverState.value!
    expect(state.snapTime).toBe(60)
    expect(state.snapX).toBe(60)
    expect(state.samples[0]).toMatchObject({ formattedValue: '60', drawnPoint: { x: 60, y: 40 } })
  })

  // A plot width the sample step does not divide leaves one column per sample pair straddling
  // both of them: the value consolidated over such a column belongs to one of the two samples,
  // and reporting it at the midpoint between them would float the focus dot off the curve.
  test('a column straddling two samples reports one of them, never the midpoint', () => {
    const hover = mountHover(
      [makeLineMetric('sloped', pointsValuedAtTheirOwnTimestamp())],
      TIME_RANGE,
      {
        consolidation: 'max',
        plotWidth: 97
      }
    )

    const states = hoverStatesAcrossPlotMiddle(hover, 0, 97)

    // Every sample is valued at its own timestamp, so a reported point is only a point of the
    // curve when its value and the time it is reported at agree.
    const reported = states.filter((state) => state.samples[0]!.drawnPoint !== null)
    expect(reported.length).toBeGreaterThan(0)
    for (const state of reported) {
      expect(state.samples[0]!.formattedValue).toBe(String(state.snapTime))
    }
  })

  test('an area dot sits where the dot of a line through the same samples sits', () => {
    const points = pointsValuedAtTheirOwnTimestamp()
    const hover = mountHover(
      [makeLineMetric('as-line', points), makeStackedMetric('as-area', points, 's1')],
      TIME_RANGE,
      { consolidation: 'max', plotWidth: 97 }
    )

    const states = hoverStatesAcrossPlotMiddle(hover, 0, 97)

    const lineDots = drawnPointsOf(states, 'as-line')
    expect(lineDots.length).toBeGreaterThan(0)
    expect(drawnPointsOf(states, 'as-area')).toEqual(lineDots)
  })

  // An inverse metric is drawn mirrored, so the top of its curve is the bucket's minimum. The
  // hover reads the buckets as fetched, where that minimum is still the minimum.
  test('an inverse metric reports the sample its mirrored curve peaks at', () => {
    const valueDomain: [number, number] = [-100, 100]
    const hover = mountHover(
      [makeInverseLineMetric('mirrored', pointsValuedAtTheirOwnTimestamp())],
      TIME_RANGE,
      { consolidation: 'max', plotWidth: 97, valueDomain }
    )
    const { yScale } = makeScales(97, valueDomain)

    const states = hoverStatesAcrossPlotMiddle(hover, 0, 97)

    const reported = states.filter((state) => state.samples[0]!.drawnPoint !== null)
    expect(reported.length).toBeGreaterThan(0)
    for (const state of reported) {
      const sample = state.samples[0]!
      expect(sample.formattedValue).toBe(String(state.snapTime))
      expect(sample.drawnPoint!.y).toBeCloseTo(yScale(-Number(sample.formattedValue)))
    }
  })

  test('a cursor over a gap stays n/a instead of snapping to a neighbouring sample', () => {
    const gappedPoints: (number | null)[] = pointsValuedAtTheirOwnTimestamp()
    const indexOfSampleAtT50 = 4
    gappedPoints[indexOfSampleAtT50] = null
    const hover = mountHover([makeLineMetric('gapped', gappedPoints)])

    hover.moveHoverTo(pointAt(53, 50))

    expect(hover.hoverState.value!.samples[0]).toMatchObject({
      formattedValue: 'n/a',
      drawnPoint: null
    })
  })
})

describe('useHover — a plot showing part of the fetched range', () => {
  const RANGE_OF_FIVE_SAMPLES = { start: 0, end: 50, step: 10 }
  const SAMPLES_VALUED_AT_THEIR_OWN_TIMESTAMP = pointsValuedAtTheirOwnTimestamp(5)

  test('a window between two samples reads the value covering the cursor, at the cursor', () => {
    const narrowerThanOneStep: [number, number] = [23, 27]
    const timeAtThePlotMiddle = 25
    const sampleCoveringTheWindow = 30
    const hover = mountHoverOverWindow(
      [makeLineMetric('coarse', SAMPLES_VALUED_AT_THEIR_OWN_TIMESTAMP)],
      RANGE_OF_FIVE_SAMPLES,
      narrowerThanOneStep
    )

    hover.moveHoverTo(pointAt(PLOT_WIDTH / 2, PLOT_HEIGHT / 2))

    const state = hover.hoverState.value!
    expect(state.samples[0]!.formattedValue).toBe(String(sampleCoveringTheWindow))
    expect(state.snapTime).toBe(timeAtThePlotMiddle)
    expect(state.samples[0]!.drawnPoint).toBeNull()
  })

  test('a cursor at the left edge snaps to the first sample on the plot, not to one before it', () => {
    const startingNearerTheSampleBeforeIt: [number, number] = [14, 44]
    const firstSampleOnThePlot = 20
    const hover = mountHoverOverWindow(
      [makeLineMetric('fine', SAMPLES_VALUED_AT_THEIR_OWN_TIMESTAMP)],
      RANGE_OF_FIVE_SAMPLES,
      startingNearerTheSampleBeforeIt
    )

    hover.moveHoverTo(pointAt(0, PLOT_HEIGHT / 2))

    expect(hover.hoverState.value!.snapTime).toBe(firstSampleOnThePlot)
  })
})

describe('useHover — one time for every metric', () => {
  const RANGE_SAMPLED_EVERY_SECOND = { start: TIME_RANGE.start, end: TIME_RANGE.end, step: 1 }
  const SAMPLES_PER_COLUMN = 2
  const PLOT_WIDTH_DENSE =
    (RANGE_SAMPLED_EVERY_SECOND.end - RANGE_SAMPLED_EVERY_SECOND.start) /
    (SAMPLES_PER_COLUMN * RANGE_SAMPLED_EVERY_SECOND.step)
  const rising = pointsValuedAtTheirOwnTimestamp(
    PLOT_WIDTH_DENSE * SAMPLES_PER_COLUMN,
    RANGE_SAMPLED_EVERY_SECOND.step
  )
  const falling = [...rising].reverse()

  const valueAtTime = (points: number[], time: number): number =>
    points[
      Math.round((time - RANGE_SAMPLED_EVERY_SECOND.start) / RANGE_SAMPLED_EVERY_SECOND.step) - 1
    ]!

  function mountMetricsWhoseColumnMaximaFallOnDifferentSamples(): ReturnType<typeof useHover> {
    return mountHover(
      [makeLineMetric('rising', rising), makeLineMetric('falling', falling)],
      RANGE_SAMPLED_EVERY_SECOND,
      { consolidation: 'max', plotWidth: PLOT_WIDTH_DENSE }
    )
  }

  test('every dot is drawn on its own curve', () => {
    const hover = mountMetricsWhoseColumnMaximaFallOnDifferentSamples()
    const { xScale, yScale } = makeScales(PLOT_WIDTH_DENSE)
    const timeAtPixel = (x: number): number => xScale.invert(x).getTime() / 1000

    const states = hoverStatesAcrossPlotMiddle(hover, 0, PLOT_WIDTH_DENSE)

    const risingDots = drawnPointsOf(states, 'rising')
    expect(risingDots.length).toBeGreaterThan(0)
    for (const dot of risingDots) {
      expect(dot.y).toBeCloseTo(yScale(valueAtTime(rising, timeAtPixel(dot.x))))
    }
    for (const dot of drawnPointsOf(states, 'falling')) {
      expect(dot.y).toBeCloseTo(yScale(valueAtTime(falling, timeAtPixel(dot.x))))
    }
  })

  test('the tooltip time applies to every value it lists', () => {
    const hover = mountMetricsWhoseColumnMaximaFallOnDifferentSamples()

    const states = hoverStatesAcrossPlotMiddle(hover, 0, PLOT_WIDTH_DENSE)

    for (const state of states) {
      const listedTimes = state.samples.map((sample) => sample.snapTime)
      expect(new Set(listedTimes)).toEqual(new Set([state.snapTime]))
    }
  })

  test('a metric without a drawn sample at the crosshair time keeps its own reading on its curve', () => {
    const SAMPLES_PER_WIDER_COLUMN = 4
    const plotWidth =
      (RANGE_SAMPLED_EVERY_SECOND.end - RANGE_SAMPLED_EVERY_SECOND.start) /
      (SAMPLES_PER_WIDER_COLUMN * RANGE_SAMPLED_EVERY_SECOND.step)
    const sampleCount = plotWidth * SAMPLES_PER_WIDER_COLUMN
    const PEAK = 60
    const peakingMidColumn = Array.from({ length: sampleCount }, (_, index) =>
      index % SAMPLES_PER_WIDER_COLUMN === 1 ? PEAK : PEAK - 10
    )
    const risingNearTheBottom = Array.from({ length: sampleCount }, (_, index) => index / 10)
    const hover = mountHover(
      [makeLineMetric('peaking', peakingMidColumn), makeLineMetric('rising', risingNearTheBottom)],
      RANGE_SAMPLED_EVERY_SECOND,
      { consolidation: 'max', plotWidth }
    )
    const { xScale, yScale } = makeScales(plotWidth)
    const timeAtPixel = (x: number): number => xScale.invert(x).getTime() / 1000

    hover.moveHoverTo(pointAt(plotWidth / 2, yScale(PEAK)))

    const state = hover.hoverState.value!
    const risingSample = state.samples.find((sample) => sample.metricName === 'rising')!
    expect(risingSample.snapTime).not.toBe(state.snapTime)
    expect(risingSample.drawnPoint).not.toBeNull()
    const { x, y } = risingSample.drawnPoint!
    expect(y).toBeCloseTo(yScale(valueAtTime(risingNearTheBottom, timeAtPixel(x))))
  })
})

describe('useHover — sample order', () => {
  test('lists a stack topmost layer first, the way it reads down the graph', () => {
    const hover = mountHover([
      makeStackedMetric('bottom', constantPoints(10), 's1'),
      makeStackedMetric('middle', constantPoints(20), 's1'),
      makeStackedMetric('top', constantPoints(30), 's1')
    ])

    hover.moveHoverTo(pointAt(50, 50))

    const listedPixelYs = hover.hoverState.value!.samples.map((sample) => sample.drawnPoint!.y)
    expect(listedPixelYs).toHaveLength(3)
    expect(listedPixelYs).toEqual([...listedPixelYs].sort((first, second) => first - second))
  })

  test('lists lines above the areas they overlay, then the mirrored half, minus the baseline', () => {
    const drawOrder = [
      makeStackedMetric('user', constantPoints(10), 's1'),
      makeStackedMetric('system', constantPoints(10), 's1'),
      makeStackedMetric('baseline', constantPoints(5), 's1', true),
      makeInverseLineMetric('outbound', constantPoints(20)),
      makeLineMetric('util', constantPoints(60))
    ]
    const hover = mountHover(drawOrder, TIME_RANGE, { valueDomain: [-100, 100] })

    hover.moveHoverTo(pointAt(50, 50))

    const listedNames = hover.hoverState.value!.samples.map((sample) => sample.metricName)
    expect(listedNames).toEqual(['util', 'system', 'user', 'outbound'])
  })

  test('the reordering keeps each sample on its own metric', () => {
    const hover = mountHover([
      makeStackedMetric('bottom', constantPoints(10), 's1'),
      makeStackedMetric('top', constantPoints(30), 's1')
    ])

    hover.moveHoverTo(pointAt(50, 50))

    const samplesByName = new Map(
      hover.hoverState.value!.samples.map((sample) => [sample.metricName, sample])
    )
    expect(samplesByName.get('bottom')!.formattedValue).toBe('10')
    expect(samplesByName.get('top')!.formattedValue).toBe('30')
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

describe('useHover — value formatting', () => {
  test('a sample renders in the axis unit the graph names', () => {
    // What "Settings > Unit > Custom > Notation: IEC" enforces on a byte graph.
    const iecBytes: Metric['metadata']['unit'] = {
      notation: 'iec',
      symbol: 'B',
      precision: { type: 'auto', digits: 2 },
      convertible: false
    }
    const mebibytes32 = 33_554_432
    const hover = mountHover(
      [makeLineMetric('mem_used', constantPoints(mebibytes32))],
      TIME_RANGE,
      {
        axisUnit: iecBytes,
        valueDomain: [0, 2 * mebibytes32]
      }
    )

    hover.moveHoverTo(pointAt(PLOT_WIDTH / 2, PLOT_HEIGHT / 2))

    expect(hover.hoverState.value!.samples[0]!.formattedValue).toBe('32 MiB')
  })
})

describe('useHover — bars', () => {
  function makeBarMetric(name: string, dataPoints: (number | null)[]): Metric {
    return {
      metadata: { name, title: name, unit: UNIT, color: '#ff0000', attributes: [] },
      render: { shape: 'bar', stack: null, aggregation: 'sum', inverse: false, hidden: false },
      data_points: dataPoints
    }
  }

  function mountBarHover(metrics: Metric[], binEdges: number[]): ReturnType<typeof useHover> {
    const hover = renderHover(metrics, TIME_RANGE, makeScales())
    const composed = composeSeries({
      metrics,
      cache: metrics.map((metric) => m4(metric.data_points, TIME_RANGE, 4000)),
      dataTimeRange: TIME_RANGE,
      visibleTimeRange: [TIME_RANGE.start, TIME_RANGE.end],
      columnCount: PLOT_WIDTH,
      binEdges
    })
    hover.recordDrawnGeometry(composed.bucketsOnPlot, composed.stacksOnPlot)
    return hover
  }

  test('reads the bin under the cursor and snaps to its centre', () => {
    const hover = mountBarHover([makeBarMetric('alerts', constantPoints(3))], [0, 50, 100])

    hover.moveHoverTo(pointAt(20, 95))

    const state = hover.hoverState.value!
    expect(state.snapInterval).toEqual({ start: 0, end: 50 })
    expect(state.snapX).toBe(25)
    expect(state.samples[0]!.formattedValue).toContain('15')
  })

  test('places the focus dot on the top of the bar', () => {
    const hover = mountBarHover([makeBarMetric('alerts', constantPoints(3))], [0, 50, 100])

    hover.moveHoverTo(pointAt(70, 95))

    expect(hover.hoverState.value!.samples[0]!.drawnPoint).toEqual({ x: 75, y: PLOT_HEIGHT - 15 })
  })

  test('snaps a graph without bars to no interval', () => {
    const hover = mountHover([makeLineMetric('cpu', constantPoints(50))])

    hover.moveHoverTo(pointAt(50, 50))

    expect(hover.hoverState.value!.snapInterval).toBeNull()
  })
})
