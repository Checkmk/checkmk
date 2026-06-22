/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import type { M4Cache } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import { drawData } from '@/graphing/components/TimeSeriesGraph/render'
import { drawLine } from '@/graphing/components/TimeSeriesGraph/render/line'
import type {
  StackedSeries,
  StackedSeriesKind
} from '@/graphing/components/TimeSeriesGraph/render/stacked'
import { drawStackedBand } from '@/graphing/components/TimeSeriesGraph/render/stacked'
import type { Metric } from '@/graphing/components/TimeSeriesGraph/types'

// drawData's only job is to dispatch to the leaf renderers in the right order with the
// right alpha; mocking them lets the assertions observe that dispatch directly.
vi.mock('@/graphing/components/TimeSeriesGraph/render/line', () => ({
  drawLine: vi.fn()
}))
vi.mock('@/graphing/components/TimeSeriesGraph/render/stacked', () => ({
  drawStackedBand: vi.fn()
}))

const drawLineSpy = vi.mocked(drawLine)
const drawStackedBandSpy = vi.mocked(drawStackedBand)

function makeSeries(kind: StackedSeriesKind): StackedSeries {
  return { kind, bands: [] }
}

function makeMetric(name: string, color: string): Metric {
  return { metadata: { name, color }, render: { stack: '', inverse: false } } as unknown as Metric
}

const xScale = (() => 0) as unknown as ScaleTime<number, number>
const yScale = (() => 0) as unknown as ScaleLinear<number, number>
const options = { interpolator: 'linear' as const }
const noBuckets: M4Cache[] = [[], [], []]

function makeCtx() {
  return { globalAlpha: 1 } as unknown as CanvasRenderingContext2D
}

describe('drawData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('routes each series to the renderer matching its kind, carrying the metric color', () => {
    const ctx = makeCtx()
    const metrics = [makeMetric('area', '#area00'), makeMetric('line', '#line00')]
    const stacks = [makeSeries('area-stacked'), makeSeries('line')]

    drawData(ctx, metrics, noBuckets, stacks, xScale, yScale, options)

    expect(drawStackedBandSpy).toHaveBeenCalledTimes(1)
    expect(drawStackedBandSpy.mock.calls[0]![4]).toBe('#area00')
    expect(drawLineSpy).toHaveBeenCalledTimes(1)
    expect(drawLineSpy.mock.calls[0]![4]).toBe('#line00')
  })

  test('paints stacked areas behind lines even when a line metric is ordered first', () => {
    const ctx = makeCtx()
    const metrics = [makeMetric('line', '#line00'), makeMetric('area', '#area00')]
    const stacks = [makeSeries('line'), makeSeries('area-stacked')]

    drawData(ctx, metrics, noBuckets, stacks, xScale, yScale, options)

    const areaDrawnAt = drawStackedBandSpy.mock.invocationCallOrder[0]!
    const lineDrawnAt = drawLineSpy.mock.invocationCallOrder[0]!
    expect(areaDrawnAt).toBeLessThan(lineDrawnAt)
  })

  test('draws the highlighted metric fully opaque and dims the others', () => {
    const ctx = makeCtx()
    const metrics = [makeMetric('focus', '#focus0'), makeMetric('other', '#other0')]
    const stacks = [makeSeries('area-stacked'), makeSeries('area-stacked')]
    const alphaByColor = new Map<string, number>()
    drawStackedBandSpy.mockImplementation((context, _series, _x, _y, color) => {
      alphaByColor.set(color, context.globalAlpha)
    })

    drawData(ctx, metrics, noBuckets, stacks, xScale, yScale, options, 'focus')

    expect(alphaByColor.get('#focus0')).toBe(1)
    expect(alphaByColor.get('#other0')).toBeLessThan(1)
  })

  test('with no metric highlighted, every series is drawn fully opaque', () => {
    const ctx = makeCtx()
    const metrics = [makeMetric('a', '#aaaaaa'), makeMetric('b', '#bbbbbb')]
    const stacks = [makeSeries('area-stacked'), makeSeries('area-stacked')]
    const alphas: number[] = []
    drawStackedBandSpy.mockImplementation((context) => {
      alphas.push(context.globalAlpha)
    })

    drawData(ctx, metrics, noBuckets, stacks, xScale, yScale, options)

    expect(alphas).toEqual([1, 1])
  })

  test('restores full opacity after drawing so later draws are unaffected', () => {
    const ctx = makeCtx()
    const metrics = [makeMetric('focus', '#focus0'), makeMetric('other', '#other0')]
    const stacks = [makeSeries('area-stacked'), makeSeries('area-stacked')]

    drawData(ctx, metrics, noBuckets, stacks, xScale, yScale, options, 'focus')

    expect(ctx.globalAlpha).toBe(1)
  })
})
