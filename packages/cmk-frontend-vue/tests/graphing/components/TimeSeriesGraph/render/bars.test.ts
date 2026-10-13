/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { scaleLinear, scaleTime } from 'd3-scale'

import type { BarRender, Metric } from '@/graphing/components/TimeSeriesGraph'
import {
  type BarSeries,
  composeBars,
  drawBars
} from '@/graphing/components/TimeSeriesGraph/render/bars'

const DATA_RANGE = { start: 0, end: 40, step: 10 }
const EDGES = [0, 20, 40]

function barMetric(
  name: string,
  dataPoints: (number | null)[],
  render: Partial<Omit<BarRender, 'shape'>> = {}
): Metric {
  return {
    metadata: {
      name,
      title: name,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: true
      },
      color: '#ff0000',
      attributes: []
    },
    render: {
      shape: 'bar',
      stack: null,
      aggregation: 'sum',
      inverse: false,
      hidden: false,
      ...render
    },
    data_points: dataPoints
  }
}

function spans(series: BarSeries | null | undefined): [number, number][] {
  return series!.bars.map((bar) => [bar.from, bar.to])
}

describe('composeBars', () => {
  it('draws a bar from zero to the sum of its bin', () => {
    const [series] = composeBars([barMetric('a', [1, 2, 3, 4])], DATA_RANGE, EDGES)

    expect(spans(series)).toEqual([
      [0, 3],
      [0, 7]
    ])
  })

  it('rests a bar on the bar below it in the same stack', () => {
    const [, upper] = composeBars(
      [barMetric('a', [1, 2, 3, 4], { stack: 's' }), barMetric('b', [1, 1, 1, 1], { stack: 's' })],
      DATA_RANGE,
      EDGES
    )

    expect(spans(upper)).toEqual([
      [3, 5],
      [7, 9]
    ])
  })

  it('hangs a mirrored bar below the baseline', () => {
    const [series] = composeBars(
      [barMetric('a', [1, 2, 3, 4], { inverse: true })],
      DATA_RANGE,
      EDGES
    )

    expect(spans(series)).toEqual([
      [-0, -3],
      [-0, -7]
    ])
  })

  it('composes nothing for a metric of another shape', () => {
    const line: Metric = {
      ...barMetric('a', [1]),
      render: { shape: 'line', inverse: false, hidden: false }
    }

    expect(composeBars([line], DATA_RANGE, null)).toEqual([null])
  })

  it('refuses a bar metric without bin edges', () => {
    expect(() => composeBars([barMetric('a', [1])], DATA_RANGE, null)).toThrow()
  })
})

describe('drawBars', () => {
  function recordFills(): {
    ctx: CanvasRenderingContext2D
    fills: [number, number, number, number][]
  } {
    const fills: [number, number, number, number][] = []
    const ctx = {
      fillStyle: '',
      fillRect: (x: number, y: number, width: number, height: number) => {
        fills.push([x, y, width, height].map(Math.round) as [number, number, number, number])
      }
    } as unknown as CanvasRenderingContext2D
    return { ctx, fills }
  }

  const xScale = scaleTime()
    .domain([new Date(0), new Date(40_000)])
    .range([0, 40])
  const yScale = scaleLinear().domain([0, 10]).range([100, 0])

  it('leaves a gap of four pixels beside a wide bar', () => {
    const { ctx, fills } = recordFills()
    const [series] = composeBars([barMetric('a', [1, 2, 3, 4])], DATA_RANGE, EDGES)

    drawBars(ctx, series!, xScale, yScale, '#ff0000')

    expect(fills).toEqual([
      [0, 70, 16, 30],
      [20, 30, 16, 70]
    ])
  })

  it('narrows the gap beside a narrow bar and drops it beside a thin one', () => {
    const { ctx, fills } = recordFills()
    const everySecond = { start: 0, end: 40, step: 1 }
    const ones = Array.from({ length: 40 }, () => 1)
    const [series] = composeBars([barMetric('a', ones)], everySecond, [0, 3, 13, 40])

    drawBars(ctx, series!, xScale, yScale, '#ff0000')

    expect(fills.map(([, , width]) => width)).toEqual([3, 9, 23])
  })

  it('skips a bin without data', () => {
    const { ctx, fills } = recordFills()
    const [series] = composeBars([barMetric('a', [null, null, 3, 4])], DATA_RANGE, EDGES)

    drawBars(ctx, series!, xScale, yScale, '#ff0000')

    expect(fills).toHaveLength(1)
  })
})
