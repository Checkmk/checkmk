/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { describe, expect, test, vi } from 'vitest'

import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import {
  type StackedBand,
  type StackedSeries,
  computeStackedSeries,
  drawStackedBand
} from '@/graphing/components/TimeSeriesGraph/render/stacked'
import type { Metric } from '@/graphing/components/TimeSeriesGraph/types'

// A single-sample bucket so every consolidation (min/max/avg) resolves to the same value,
// keeping the stacking assertions independent of the consolidation function.
function makeBucket(value: number): M4Bucket {
  return {
    startTime: 0,
    endTime: 1,
    gap: false,
    minValue: value,
    maxValue: value,
    minValueTime: 0,
    maxValueTime: 0,
    firstValue: value,
    firstValueTime: 0,
    lastValue: value,
    lastValueTime: 0,
    sampleCount: 1,
    valueSum: value
  }
}

function makeGapBucket(): M4Bucket {
  return { ...makeBucket(NaN), gap: true, sampleCount: 0, valueSum: 0 }
}

// computeStackedSeries only consults render.stack; the rest of Metric is irrelevant here.
function makeMetric(stack: string): Metric {
  return { render: { stack, inverse: false } } as unknown as Metric
}

describe('computeStackedSeries', () => {
  test('an unstacked metric becomes a line resting on the zero baseline', () => {
    const value = 5
    const metrics = [makeMetric('')]
    const buckets = [[makeBucket(value)]]

    const [lineSeries] = computeStackedSeries(metrics, buckets, 'avg')

    expect(lineSeries!.kind).toBe('line')
    expect(lineSeries!.bands[0]).toMatchObject({ lower: 0, upper: value })
  })

  test('metrics in the same group stack cumulatively, each layer resting on the one below', () => {
    const baseValue = 2
    const layerValue = 4
    const metrics = [makeMetric('g1'), makeMetric('g1')]
    const buckets = [[makeBucket(baseValue)], [makeBucket(layerValue)]]

    const [base, layer] = computeStackedSeries(metrics, buckets, 'avg')

    expect(base!.bands[0]).toMatchObject({ lower: 0, upper: baseValue })
    expect(layer!.bands[0]!.lower).toBe(base!.bands[0]!.upper)
    expect(layer!.bands[0]!.upper).toBe(layer!.bands[0]!.lower + layerValue)
  })

  test('a metric in one group is unaffected by the running sum of another group', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1'), makeMetric('g2')]
    const buckets = [[makeBucket(2)], [makeBucket(4)], [makeBucket(7)]]

    const series = computeStackedSeries(metrics, buckets, 'avg')

    const otherGroup = series[2]!
    expect(otherGroup.bands[0]!.lower).toBe(0)
  })

  test('an unstacked line between areas does not raise the stack above it', () => {
    const baseValue = 2
    const lineValue = 99
    const topValue = 3
    const metrics = [makeMetric('g1'), makeMetric(''), makeMetric('g1')]
    const buckets = [[makeBucket(baseValue)], [makeBucket(lineValue)], [makeBucket(topValue)]]

    const [base, middle, top] = computeStackedSeries(metrics, buckets, 'avg')

    expect(middle!.kind).toBe('line')
    expect(top!.bands[0]!.lower).toBe(base!.bands[0]!.upper)
    expect(top!.bands[0]!.upper).toBe(top!.bands[0]!.lower + topValue)
  })

  test('a gap bucket in the base does not advance the cumulative sum', () => {
    const layerValue = 4
    const metrics = [makeMetric('g1'), makeMetric('g1')]
    const buckets = [[makeGapBucket()], [makeBucket(layerValue)]]

    const [base, layer] = computeStackedSeries(metrics, buckets, 'avg')

    expect(base!.bands[0]!.gap).toBe(true)
    expect(layer!.bands[0]!.lower).toBe(0)
    expect(layer!.bands[0]!.upper).toBe(layer!.bands[0]!.lower + layerValue)
  })
})

function makeSpyCtx() {
  return {
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 0
  }
}

function makeBand(overrides: Partial<StackedBand> = {}): StackedBand {
  return { lower: 0, upper: 1, gap: false, startTime: 0, endTime: 1, ...overrides }
}

const xScale = ((date: Date) => date.getTime() / 1000) as unknown as ScaleTime<number, number>
const yScale = ((value: number) => value) as unknown as ScaleLinear<number, number>

describe('drawStackedBand', () => {
  test('fills and strokes one closed polygon for a contiguous run of bands', () => {
    const ctx = makeSpyCtx()
    const series: StackedSeries = {
      kind: 'area-stacked',
      bands: [makeBand({ upper: 1 }), makeBand({ upper: 2 }), makeBand({ upper: 3 })]
    }

    drawStackedBand(ctx as unknown as CanvasRenderingContext2D, series, xScale, yScale, '#3366cc')

    expect(ctx.closePath).toHaveBeenCalledTimes(1)
    expect(ctx.fill).toHaveBeenCalledTimes(1)
    expect(ctx.stroke).toHaveBeenCalledTimes(1)
  })

  test('a gap splits the area into separate filled polygons', () => {
    const ctx = makeSpyCtx()
    const series: StackedSeries = {
      kind: 'area-stacked',
      bands: [makeBand(), makeBand({ gap: true }), makeBand()]
    }

    drawStackedBand(ctx as unknown as CanvasRenderingContext2D, series, xScale, yScale, '#3366cc')

    expect(ctx.fill).toHaveBeenCalledTimes(2)
    expect(ctx.closePath).toHaveBeenCalledTimes(2)
  })

  test('outlines the area in the solid color and fills it at the requested opacity', () => {
    const ctx = makeSpyCtx()
    const color = '#3366cc'
    const fillOpacity = 0.3
    const series: StackedSeries = { kind: 'area-stacked', bands: [makeBand(), makeBand()] }

    drawStackedBand(
      ctx as unknown as CanvasRenderingContext2D,
      series,
      xScale,
      yScale,
      color,
      fillOpacity
    )

    expect(ctx.strokeStyle).toBe(color)
    expect(ctx.fillStyle).toMatch(new RegExp(`^rgba\\(\\d+, \\d+, \\d+, ${fillOpacity}\\)$`))
  })
})
