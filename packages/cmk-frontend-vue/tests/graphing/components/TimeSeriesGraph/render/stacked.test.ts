/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { describe, expect, test } from 'vitest'

import { m4 } from '@/graphing/components/TimeSeriesGraph/decimation/decimate'
import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import { keptSamples } from '@/graphing/components/TimeSeriesGraph/render/bucket'
import {
  type TimeValuePoint,
  clampedValueAt
} from '@/graphing/components/TimeSeriesGraph/render/polyline'
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

function decimatedIntoOneBucket(...values: (number | null)[]): M4Bucket {
  const [bucket] = m4(values, { start: 0, end: values.length * STEP, step: STEP }, 1)
  return bucket!
}

// computeStackedSeries only consults the render; the rest of Metric is irrelevant here.
function makeMetric(stack: string | null): Metric {
  return {
    render:
      stack === null
        ? { shape: 'line', inverse: false, hidden: false }
        : { shape: 'area', stack, inverse: false, hidden: false }
  } as unknown as Metric
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
    const [series] = computeStackedSeries([makeMetric(null)], [[decimatedIntoOneBucket(5)]])

    expect(series!.kind).toBe('line')
  })

  test('a lone area rests on the zero baseline', () => {
    const value = 5

    const [area] = computeStackedSeries([makeMetric('g1')], [[decimatedIntoOneBucket(value)]])

    expect(firstColumn(area).vertices).toEqual([{ time: STEP, lower: 0, upper: value }])
  })

  test('an area passes through every sample the bucket kept, each at its own time', () => {
    const bucket = decimatedIntoOneBucket(1, 9, 1)

    const [area] = computeStackedSeries([makeMetric('g1')], [[bucket]])

    expect(upperEdgeOf(firstColumn(area))).toEqual(keptSamples(bucket))
  })

  test('metrics in the same group stack cumulatively, each layer resting on the one below', () => {
    const layerValue = 4
    const metrics = [makeMetric('g1'), makeMetric('g1')]

    const [base, layer] = computeStackedSeries(metrics, [
      [decimatedIntoOneBucket(2)],
      [decimatedIntoOneBucket(layerValue)]
    ])

    const [baseVertex] = firstColumn(base).vertices
    const [layerVertex] = firstColumn(layer).vertices
    expect(layerVertex!.lower).toBe(baseVertex!.upper)
    expect(layerVertex!.upper).toBe(layerVertex!.lower + layerValue)
  })

  test('a metric in one group is unaffected by the running sum of another group', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1'), makeMetric('g2')]

    const series = computeStackedSeries(metrics, [
      [decimatedIntoOneBucket(2)],
      [decimatedIntoOneBucket(4)],
      [decimatedIntoOneBucket(7)]
    ])

    expect(firstColumn(series[2]).vertices[0]!.lower).toBe(0)
  })

  test('an unstacked line between areas does not raise the stack above it', () => {
    const metrics = [makeMetric('g1'), makeMetric(null), makeMetric('g1')]

    const [base, , top] = computeStackedSeries(metrics, [
      [decimatedIntoOneBucket(2)],
      [decimatedIntoOneBucket(99)],
      [decimatedIntoOneBucket(3)]
    ])

    expect(firstColumn(top).vertices[0]!.lower).toBe(firstColumn(base).vertices[0]!.upper)
  })

  test('a layer rests on the layer below at every sample even when they peak on different samples', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1')]
    const rising = decimatedIntoOneBucket(3, 7)
    const falling = decimatedIntoOneBucket(7, 3)

    const [base, top] = computeStackedSeries(metrics, [[rising], [falling]])

    const topColumn = firstColumn(top)
    expect(topColumn.vertices.length).toBeGreaterThan(1)
    for (const vertex of topColumn.vertices) {
      expect(vertex.lower).toBe(clampedValueAt(upperEdgeOf(firstColumn(base)), vertex.time))
    }
  })

  test('a layer bends wherever the layer below bends, so the stack stays closed', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1')]
    const peaking = decimatedIntoOneBucket(1, 9, 1)
    const flat = decimatedIntoOneBucket(2, 2, 2)

    const [base, top] = computeStackedSeries(metrics, [[peaking], [flat]])

    const bendsBelow = timesOf(firstColumn(base))
    expect(timesOf(firstColumn(top))).toEqual(expect.arrayContaining(bendsBelow))
    for (const vertex of firstColumn(top).vertices) {
      expect(vertex.lower).toBe(clampedValueAt(upperEdgeOf(firstColumn(base)), vertex.time))
    }
  })

  test('a gap in the base does not raise the layer above it', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1')]

    const [, layer] = computeStackedSeries(metrics, [
      [decimatedIntoOneBucket(null)],
      [decimatedIntoOneBucket(4)]
    ])

    expect(firstColumn(layer).vertices[0]!.lower).toBe(0)
  })

  test('a gap in a middle layer leaves the layer below as the base of the next one', () => {
    const metrics = [makeMetric('g1'), makeMetric('g1'), makeMetric('g1')]

    const [base, , top] = computeStackedSeries(metrics, [
      [decimatedIntoOneBucket(2)],
      [decimatedIntoOneBucket(null)],
      [decimatedIntoOneBucket(3)]
    ])

    expect(firstColumn(top).vertices[0]!.lower).toBe(firstColumn(base).vertices[0]!.upper)
  })
})

type PathCommand = ['moveTo' | 'lineTo', number, number] | ['closePath']

interface FilledPath {
  commands: PathCommand[]
  fillStyle: string
}

interface StrokedPath {
  commands: PathCommand[]
  strokeStyle: string
  lineWidth: number
  lineCap: CanvasLineCap
  lineJoin: CanvasLineJoin
}

function makeRecordingCtx() {
  let commands: PathCommand[] = []
  const filled: FilledPath[] = []
  const stroked: StrokedPath[] = []
  const recorder = {
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    lineCap: 'butt' as CanvasLineCap,
    lineJoin: 'miter' as CanvasLineJoin,
    beginPath() {
      commands = []
    },
    moveTo(x: number, y: number) {
      commands.push(['moveTo', x, y])
    },
    lineTo(x: number, y: number) {
      commands.push(['lineTo', x, y])
    },
    closePath() {
      commands.push(['closePath'])
    },
    fill() {
      filled.push({ commands: [...commands], fillStyle: recorder.fillStyle })
    },
    stroke() {
      stroked.push({
        commands: [...commands],
        strokeStyle: recorder.strokeStyle,
        lineWidth: recorder.lineWidth,
        lineCap: recorder.lineCap,
        lineJoin: recorder.lineJoin
      })
    }
  }
  return { ctx: recorder as unknown as CanvasRenderingContext2D, filled, stroked }
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

const COLOR = '#3366cc'

describe('drawStackedBand', () => {
  test('paints a contiguous run of columns as one band', () => {
    const { ctx, filled, stroked } = makeRecordingCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }),
      makeColumn({ time: 1, lower: 0, upper: 2 }),
      makeColumn({ time: 2, lower: 0, upper: 3 })
    )

    drawStackedBand(ctx, series, xScale, yScale, COLOR)

    expect(filled).toHaveLength(1)
    expect(stroked).toHaveLength(1)
  })

  test('a gap splits the area into separate bands', () => {
    const { ctx, filled, stroked } = makeRecordingCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }),
      GAP_COLUMN,
      makeColumn({ time: 2, lower: 0, upper: 1 })
    )

    drawStackedBand(ctx, series, xScale, yScale, COLOR)

    expect(filled).toHaveLength(2)
    expect(stroked).toHaveLength(2)
  })

  test('fills along the upper edge forward and the lower edge back, each vertex at its own time', () => {
    const { ctx, filled } = makeRecordingCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }, { time: 1, lower: 0, upper: 2 }),
      makeColumn({ time: 2, lower: 1, upper: 3 })
    )

    drawStackedBand(ctx, series, xScale, yScale, COLOR)

    expect(filled[0]!.commands).toEqual([
      ['moveTo', 0, 1],
      ['lineTo', 1, 2],
      ['lineTo', 2, 3],
      ['lineTo', 2, 1],
      ['lineTo', 1, 0],
      ['lineTo', 0, 0],
      ['closePath']
    ])
  })

  test('strokes the upper edge only, neither the lower edge nor the sides', () => {
    const { ctx, stroked } = makeRecordingCtx()
    const series = makeArea(
      makeColumn({ time: 0, lower: 0, upper: 1 }, { time: 1, lower: 0, upper: 2 }),
      makeColumn({ time: 2, lower: 1, upper: 3 })
    )

    drawStackedBand(ctx, series, xScale, yScale, COLOR)

    expect(stroked[0]!.commands).toEqual([
      ['moveTo', 0, 1],
      ['lineTo', 1, 2],
      ['lineTo', 2, 3]
    ])
  })

  test('fills the band at 35 % of its color', () => {
    const { ctx, filled } = makeRecordingCtx()
    const series = makeArea(makeColumn({ time: 0, lower: 0, upper: 1 }))

    drawStackedBand(ctx, series, xScale, yScale, COLOR)

    expect(filled[0]!.fillStyle).toBe('rgba(51, 102, 204, 0.35)')
  })

  test('strokes the edge in the solid color, 2 px wide with round caps and joins', () => {
    const { ctx, stroked } = makeRecordingCtx()
    const series = makeArea(makeColumn({ time: 0, lower: 0, upper: 1 }))

    drawStackedBand(ctx, series, xScale, yScale, COLOR)

    expect(stroked[0]).toMatchObject({
      strokeStyle: COLOR,
      lineWidth: 2,
      lineCap: 'round',
      lineJoin: 'round'
    })
  })
})
