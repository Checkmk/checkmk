/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { describe, expect, test, vi } from 'vitest'

import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import { drawLine } from '@/graphing/components/TimeSeriesGraph/render/line'

function makeSpyCtx() {
  return {
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    strokeStyle: '',
    lineWidth: 0
  }
}

// Defaults every numeric field to NaN so a gap bucket (overriding only gap:true)
// carries NaN everywhere. If drawLine failed to skip it, that NaN would surface
// as a lineTo argument and fail the finiteness assertion in the gap test.
function makeBucket(overrides: Partial<M4Bucket>): M4Bucket {
  return {
    startTime: NaN,
    endTime: NaN,
    gap: false,
    minValue: NaN,
    maxValue: NaN,
    minValueTime: NaN,
    maxValueTime: NaN,
    firstValue: NaN,
    firstValueTime: NaN,
    lastValue: NaN,
    lastValueTime: NaN,
    sampleCount: NaN,
    valueSum: NaN,
    ...overrides
  }
}

describe('drawLine', () => {
  const buckets: M4Bucket[] = [
    makeBucket({
      minValue: 1,
      maxValue: 3,
      minValueTime: 0,
      maxValueTime: 9,
      firstValue: 1,
      firstValueTime: 0,
      lastValue: 3,
      lastValueTime: 9
    }),
    makeBucket({
      minValue: 2,
      maxValue: 4,
      minValueTime: 10,
      maxValueTime: 19,
      firstValue: 2,
      firstValueTime: 10,
      lastValue: 4,
      lastValueTime: 19
    })
  ]
  const xScale = ((date: Date) => date.getTime() / 1000) as unknown as ScaleTime<number, number>
  const yScale = ((value: number) => value) as unknown as ScaleLinear<number, number>

  test('draws a min→max vertical per bucket', () => {
    const ctx = makeSpyCtx()

    drawLine(ctx as unknown as CanvasRenderingContext2D, buckets, xScale, yScale, '#333')

    // 2 buckets → at least 2 vertical pairs (moveTo + lineTo)
    expect(ctx.moveTo.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(ctx.lineTo.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(ctx.stroke).toHaveBeenCalled()
  })

  test('gaps lift the pen: no lineTo is ever issued with a NaN coordinate', () => {
    const withGap: M4Bucket[] = [buckets[0]!, makeBucket({ gap: true }), buckets[1]!]
    const ctx = makeSpyCtx()

    drawLine(ctx as unknown as CanvasRenderingContext2D, withGap, xScale, yScale, '#333')

    const coordinates = ctx.lineTo.mock.calls.flat()
    const nonFiniteCoordinates = coordinates.filter((coordinate) => !Number.isFinite(coordinate))

    expect(nonFiniteCoordinates).toEqual([])
  })
})
