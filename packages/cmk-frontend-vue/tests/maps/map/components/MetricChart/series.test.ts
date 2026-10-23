/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type SeriesContext,
  buildGraphMetrics,
  buildThresholdLines,
  seriesColorMap
} from '@/maps/map/components/MetricChart/series'
import type { MetricPoint, MetricUnitSpec } from '@/maps/types/api'

const GRID = { start: 0, end: 120, step: 60, count: 2 }

const PALETTE = ['rgb(1 1 1)', 'rgb(2 2 2)']

function point(ts: number, value: number, unit = ''): MetricPoint {
  return { ts, value, unit }
}

function context(overrides: Partial<SeriesContext> = {}): SeriesContext {
  return { palette: PALETTE, ...overrides }
}

const BYTES: MetricUnitSpec = {
  notation: 'iec',
  symbol: 'B',
  precision: { type: 'strict', digits: 1 },
  scale: 1
}

describe('buildGraphMetrics', () => {
  it('applies the registry translation scale, so the graph plots canonical units', () => {
    const metrics = buildGraphMetrics(
      { if_in: [point(0, 100)] },
      ['if_in'],
      GRID,
      context({ unitMap: { if_in: { ...BYTES, scale: 8 } } })
    )
    expect(metrics[0]!.data_points![0]).toBe(800)
  })

  it('hands over the registry unit without its scale, since the values arrive scaled', () => {
    const metrics = buildGraphMetrics(
      { mem: [point(0, 1)] },
      ['mem'],
      GRID,
      context({ unitMap: { mem: { ...BYTES, scale: 1024 } } })
    )
    expect(metrics[0]!.metadata.unit).toEqual({
      notation: 'iec',
      symbol: 'B',
      precision: { type: 'strict', digits: 1 },
      convertible: true
    })
  })

  it('reads a magnitude prefix off the raw unit where the registry knows nothing', () => {
    const metrics = buildGraphMetrics({ exotic: [point(0, 2, 'MB')] }, ['exotic'], GRID, context())
    expect(metrics[0]!.data_points![0]).toBe(2e6)
    expect(metrics[0]!.metadata.unit).toEqual({
      notation: 'si',
      symbol: 'B',
      precision: { type: 'auto', digits: 2 },
      convertible: true
    })
  })

  it("draws a metric in Checkmk's own colour for it", () => {
    const metrics = buildGraphMetrics(
      { load1: [point(0, 1)] },
      ['load1'],
      GRID,
      context({ colorMap: { load1: '#15d1a0' } })
    )
    expect(metrics[0]!.metadata.color).toBe('#15d1a0')
  })

  it('falls back to the palette, cycling through it for a wide graph', () => {
    const data = { a: [point(0, 1)], b: [point(0, 1)], c: [point(0, 1)] }
    const metrics = buildGraphMetrics(data, ['a', 'b', 'c'], GRID, context())
    expect(metrics.map((metric) => metric.metadata.color)).toEqual([
      PALETTE[0],
      PALETTE[1],
      PALETTE[0]
    ])
  })

  it('degrades to the inherited colour where the palette did not resolve', () => {
    const metrics = buildGraphMetrics({ a: [point(0, 1)] }, ['a'], GRID, { palette: [] })
    expect(metrics[0]!.metadata.color).toBe('currentColor')
  })

  it("marks a bidirectional graph's lower half inverse rather than negating it", () => {
    const metrics = buildGraphMetrics(
      { in: [point(0, 5)], out: [point(0, 5)] },
      ['in', 'out'],
      GRID,
      context({ mirroredKeys: ['out'] })
    )
    expect(metrics.map((metric) => metric.render.inverse)).toEqual([false, true])
    expect(metrics[1]!.data_points![0]).toBe(5)
  })

  it('labels a series by its registry title, falling back to the raw label', () => {
    const metrics = buildGraphMetrics(
      { load1: [point(0, 1)], raw: [point(0, 1)] },
      ['load1', 'raw'],
      GRID,
      context({ titles: { load1: '1 min load' } })
    )
    expect(metrics.map((metric) => metric.metadata.title)).toEqual(['1 min load', 'raw'])
  })

  it('keeps an unfetched series in the graph, as a run of gaps', () => {
    const metrics = buildGraphMetrics({}, ['absent'], GRID, context())
    expect(metrics[0]!.data_points).toEqual([null, null])
  })
})

describe('buildThresholdLines', () => {
  const data = { fs_used: [point(0, 1)] }

  it('draws the levels of the leading metric, scaled like its curve', () => {
    const lines = buildThresholdLines(
      { warn: 80, crit: 90 },
      data,
      'fs_used',
      context({ unitMap: { fs_used: { ...BYTES, scale: 2 } } }),
      { warn: 'Warning', crit: 'Critical' },
      { warn: 'yellow', crit: 'red' }
    )
    expect(lines.map((line) => [line.name, line.value, line.color])).toEqual([
      ['warn', 160, 'yellow'],
      ['crit', 180, 'red']
    ])
  })

  it('omits a level the check does not report', () => {
    const lines = buildThresholdLines(
      { warn: null, crit: 90 },
      data,
      'fs_used',
      context(),
      { warn: 'Warning', crit: 'Critical' },
      { warn: 'yellow', crit: 'red' }
    )
    expect(lines.map((line) => line.name)).toEqual(['crit'])
  })

  it('draws nothing without levels, or without a metric to hang them on', () => {
    const labels = { warn: 'Warning', crit: 'Critical' }
    const colors = { warn: 'yellow', crit: 'red' }
    expect(buildThresholdLines(null, data, 'fs_used', context(), labels, colors)).toEqual([])
    expect(
      buildThresholdLines({ warn: 1, crit: 2 }, data, undefined, context(), labels, colors)
    ).toEqual([])
  })
})

describe('seriesColorMap', () => {
  it('resolves the same colours the curves are drawn in, so a legend agrees', () => {
    const ctx = context({ colorMap: { a: '#abcdef' } })
    const metrics = buildGraphMetrics({ a: [point(0, 1)], b: [point(0, 1)] }, ['a', 'b'], GRID, ctx)
    const colors = seriesColorMap(['a', 'b'], ctx)
    expect(colors).toEqual({
      a: metrics[0]!.metadata.color,
      b: metrics[1]!.metadata.color
    })
  })
})
