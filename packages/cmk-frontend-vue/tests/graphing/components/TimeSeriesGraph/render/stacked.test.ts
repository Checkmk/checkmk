/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { describe, expect, test, vi } from 'vitest'

import { m4 } from '@/graphing/components/TimeSeriesGraph/decimation/decimate'
import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import { keptSamples } from '@/graphing/components/TimeSeriesGraph/render/bucket'
import { type TimeValuePoint, valueAt } from '@/graphing/components/TimeSeriesGraph/render/polyline'
import {
  type AreaSeries,
  type StackedColumn,
  type StackedSeries,
  type StackedVertex,
  computeStackedSeries,
  drawStackedBand
} from '@/graphing/components/TimeSeriesGraph/render/stacked'
import type { Metric } from '@/graphing/components/TimeSeriesGraph/types'

const STEP = 10

// One bucket over all the values, the way the decimation builds it: the values are sampled at
// 10, 20, 30, ... and the bucket keeps the first, the last and the extremes among them.
function bucketOf(...values: (number | null)[]): M4Bucket {
  const [bucket] = m4(values, { start: 0, end: values.length * STEP, step: STEP }, 1)
  return bucket!
}

// computeStackedSeries only consults render.stack; the rest of Metric is irrelevant here.
function makeMetric(stack: string | null): Metric {
  return { render: { stack, inverse: false } } as unknown as Metric
}

function firstColumn(series: StackedSeries | undefined): StackedColumn {
  if (series?.kind !== 'area-stacked') {
    throw new Error('expected an area series')
  }
  return series.columns[0]!
}

const timesOf = (column: StackedColumn): number[] => column.vertices.map((vertex) => vertex.time)

const upperEdgeOf = (column: StackedColumn): TimeValuePoint[] =>
  column.vertices.map((vertex) => ({ time: vertex.time, value: vertex.upper }))

describe('computeStackedSeries', () => {
  test('an unstacked metric is drawn as a line', () => {
    const [series] = computeStackedSeries([makeMetric(null)], [[bucketOf(5)]])

    expect(series!.kind).toBe('line')
  })

  test('a lone area rests on the zero baseline', () => {
    const value = 5

    const [area] = computeStackedSeries([makeMetric('g1')], [[bucketOf(value)]])

    expect(firstColumn(area).vertices).toEqual([{ time: STEP, lower: 0, upper: value }])
  })

  test('an area passes through every sample the bucket kept, each at its own time', () => {
    const bucket = bucketOf(1, 9, 1)

    const [area] = computeStackedSeries([makeMetric('g1')], [[bucket]])

    expect(upperEdgeOf(firstColumn(area))).toEqual(keptSamples(bucket))
  })

  test('metrics in the same group stack cumulatively, each layer resting on the one below', () => {
    const layerValue = 4
    const metrics = [makeMetric('g1'), makeMetric('g1')]

    const [base, layer] = computeStackedSeries(metrics, [[bucketOf(2)], [bucketOf(layerValue)]])

    const [baseVertex] = firstColumn(base).vertices
    const [layerVertex] = firstColumn(layer).vertices
    expect(layerVertex!.lower).toBe(baseVertex!.upper)
    expect(layerVertex!.upper).toBe(layerVertex!.lower + layerValue)
  })

  test('a metric in one group is unaffected by the running sum of another group', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1'), makeMetric('g2')]

    const series = computeStackedSeries(metrics, [[bucketOf(2)], [bucketOf(4)], [bucketOf(7)]])

    expect(firstColumn(series[2]).vertices[0]!.lower).toBe(0)
  })

  test('an unstacked line between areas does not raise the stack above it', () => {
    const metrics = [makeMetric('g1'), makeMetric(null), makeMetric('g1')]

    const [base, , top] = computeStackedSeries(metrics, [
      [bucketOf(2)],
      [bucketOf(99)],
      [bucketOf(3)]
    ])

    expect(firstColumn(top).vertices[0]!.lower).toBe(firstColumn(base).vertices[0]!.upper)
  })

  test('a layer rests on the layer below at every sample even when they peak on different samples', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1')]
    const rising = bucketOf(3, 7)
    const falling = bucketOf(7, 3)

    const [base, top] = computeStackedSeries(metrics, [[rising], [falling]])

    const topColumn = firstColumn(top)
    expect(topColumn.vertices.length).toBeGreaterThan(1)
    for (const vertex of topColumn.vertices) {
      expect(vertex.lower).toBe(valueAt(upperEdgeOf(firstColumn(base)), vertex.time))
    }
  })

  test('a layer bends wherever the layer below bends, so the stack stays closed', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1')]
    const peaking = bucketOf(1, 9, 1)
    const flat = bucketOf(2, 2, 2)

    const [base, top] = computeStackedSeries(metrics, [[peaking], [flat]])

    const bendsBelow = timesOf(firstColumn(base))
    expect(timesOf(firstColumn(top))).toEqual(expect.arrayContaining(bendsBelow))
    for (const vertex of firstColumn(top).vertices) {
      expect(vertex.lower).toBe(valueAt(upperEdgeOf(firstColumn(base)), vertex.time))
    }
  })

  test('a gap in the base does not raise the layer above it', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1')]

    const [, layer] = computeStackedSeries(metrics, [[bucketOf(null)], [bucketOf(4)]])

    expect(firstColumn(layer).vertices[0]!.lower).toBe(0)
  })

  test('a gap in a middle layer leaves the layer below as the base of the next one', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1'), makeMetric('g1')]

    const [base, , top] = computeStackedSeries(metrics, [
      [bucketOf(2)],
      [bucketOf(null)],
      [bucketOf(3)]
    ])

    expect(firstColumn(top).vertices[0]!.lower).toBe(firstColumn(base).vertices[0]!.upper)
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

function makeColumn(...vertices: StackedVertex[]): StackedColumn {
  return { gap: false, vertices }
}

const GAP_COLUMN: StackedColumn = { gap: true, vertices: [] }

function makeArea(...columns: StackedColumn[]): AreaSeries {
  return { kind: 'area-stacked', columns }
}

const xScale = ((date: Date) => date.getTime() / 1000) as unknown as ScaleTime<number, number>
const yScale = ((value: number) => value) as unknown as ScaleLinear<number, number>

describe('drawStackedBand', () => {
  test('fills and strokes one closed polygon for a contiguous run of columns', () => {
    const ctx = makeSpyCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }),
      makeColumn({ time: 1, lower: 0, upper: 2 }),
      makeColumn({ time: 2, lower: 0, upper: 3 })
    )

    drawStackedBand(ctx as unknown as CanvasRenderingContext2D, series, xScale, yScale, '#3366cc')

    expect(ctx.closePath).toHaveBeenCalledTimes(1)
    expect(ctx.fill).toHaveBeenCalledTimes(1)
    expect(ctx.stroke).toHaveBeenCalledTimes(1)
  })

  test('a gap splits the area into separate filled polygons', () => {
    const ctx = makeSpyCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }),
      GAP_COLUMN,
      makeColumn({ time: 2, lower: 0, upper: 1 })
    )

    drawStackedBand(ctx as unknown as CanvasRenderingContext2D, series, xScale, yScale, '#3366cc')

    expect(ctx.fill).toHaveBeenCalledTimes(2)
    expect(ctx.closePath).toHaveBeenCalledTimes(2)
  })

  test('traces the upper edge forward and the lower edge back, each vertex at its own time', () => {
    const ctx = makeSpyCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }, { time: 1, lower: 0, upper: 2 }),
      makeColumn({ time: 2, lower: 1, upper: 3 })
    )
    const vertices = series.columns.flatMap((column) => column.vertices)

    drawStackedBand(ctx as unknown as CanvasRenderingContext2D, series, xScale, yScale, '#3366cc')

    const [start, ...upperEdgeForward] = vertices.map((vertex) => [vertex.time, vertex.upper])
    const lowerEdgeBack = [...vertices].reverse().map((vertex) => [vertex.time, vertex.lower])
    expect(ctx.moveTo.mock.calls).toEqual([start])
    expect(ctx.lineTo.mock.calls).toEqual([...upperEdgeForward, ...lowerEdgeBack])
  })

  test('outlines the area in the solid color and fills it at the requested opacity', () => {
    const ctx = makeSpyCtx()
    const color = '#3366cc'
    const fillOpacity = 0.3
    const series = makeArea(makeColumn({ time: 0, lower: 0, upper: 1 }))

    drawStackedBand(ctx as unknown as CanvasRenderingContext2D, series, xScale, yScale, color, {
      fillOpacity
    })

    expect(ctx.strokeStyle).toBe(color)
    expect(ctx.fillStyle).toMatch(new RegExp(`^rgba\\(\\d+, \\d+, \\d+, ${fillOpacity}\\)$`))
  })
})
