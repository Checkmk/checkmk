/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  composeSeries,
  composedValueDomain,
  createM4CacheStore,
  withoutOffPlotNeighbours
} from '@/graphing/components/TimeSeriesGraph/render/composeSeries'
import type { Metric, TimeRange } from '@/graphing/components/TimeSeriesGraph/types'

const STEP = 10
const DATA_RANGE: TimeRange = { start: 0, end: 100, step: STEP }
const COLUMNS = 10
const M4_BUCKETS = 4000

function makeMetric(dataPoints: (number | null)[], render: Partial<Metric['render']> = {}): Metric {
  return {
    data_points: dataPoints,
    render: { stack: null, inverse: false, hidden: false, ...render },
    metadata: { name: 'm', color: '#3366cc' }
  } as unknown as Metric
}

function compose(metrics: Metric[], dataRange: TimeRange = DATA_RANGE) {
  const cache = createM4CacheStore(M4_BUCKETS).ensure(metrics, dataRange)
  return composeSeries({
    metrics,
    cache,
    visibleTimeRange: [dataRange.start, dataRange.end],
    columnCount: COLUMNS,
    consolidation: 'max'
  })
}

const finiteValues = (values: number[]): number[] =>
  values.filter((value) => Number.isFinite(value))

describe('composeSeries', () => {
  test('routes a metric with no stack group to a line and a grouped one to a stacked area', () => {
    const composed = compose([makeMetric([1, 2, 3]), makeMetric([1, 2, 3], { stack: 'g1' })])

    expect(composed.stacks[0]!.kind).toBe('line')
    expect(composed.stacks[1]!.kind).toBe('area-stacked')
  })

  test('flanks the on-plot buckets with one off-plot neighbour on each side', () => {
    const composed = compose([makeMetric([1, 2, 3])])

    expect(composed.paddedBuckets[0]).toHaveLength(composed.bucketsOnPlot[0]!.length + 2)
    expect(withoutOffPlotNeighbours(composed.paddedBuckets[0]!)).toEqual(composed.bucketsOnPlot[0])
  })

  test('mirrors an inverse metric below the baseline', () => {
    const values = [1, 2, 3]

    const upright = compose([makeMetric(values)])
    const mirrored = compose([makeMetric(values, { inverse: true })])

    const peakOf = (composed: ReturnType<typeof compose>) =>
      Math.max(...finiteValues(composed.paddedBuckets[0]!.map((bucket) => bucket.maxValue)))
    const troughOf = (composed: ReturnType<typeof compose>) =>
      Math.min(...finiteValues(composed.paddedBuckets[0]!.map((bucket) => bucket.minValue)))

    expect(troughOf(mirrored)).toBe(-peakOf(upright))
  })

  test('keeps hidden stack references in the composition so they still raise the stack base', () => {
    const baseline = 10
    const member = 4
    const composed = compose([
      makeMetric([baseline], { stack: 'g1', hidden: true }),
      makeMetric([member], { stack: 'g1' })
    ])

    const memberBands = withoutOffPlotNeighbours(composed.stacks[1]!.bands).filter(
      (band) => !band.gap
    )
    expect(memberBands.length).toBeGreaterThan(0)
    for (const band of memberBands) {
      expect(band.lower).toBe(baseline)
      expect(band.upper).toBe(baseline + member)
    }
  })
})

describe('composedValueDomain', () => {
  test('a line metric contributes its own extremes rather than a baseline at zero', () => {
    const values = [40, 50, 60]
    const metrics = [makeMetric(values)]

    const [yMin, yMax] = composedValueDomain(metrics, compose(metrics))

    expect(yMin).toBe(Math.min(...values))
    expect(yMax).toBe(Math.max(...values))
  })

  test('stacked metrics contribute the cumulative extent of the group, not their own', () => {
    const base = 3
    const layer = 5
    const metrics = [makeMetric([base], { stack: 'g1' }), makeMetric([layer], { stack: 'g1' })]

    const [yMin, yMax] = composedValueDomain(metrics, compose(metrics))

    expect(yMin).toBe(0)
    expect(yMax).toBe(base + layer)
  })

  test('a flat series widens upward so its floor is never pushed below what the data reaches', () => {
    const flat = 7
    const metrics = [makeMetric([flat, flat, flat])]

    const [yMin, yMax] = composedValueDomain(metrics, compose(metrics))

    expect(yMin).toBe(flat)
    expect(yMax).toBeGreaterThan(flat)
  })

  test('any inverse metric forces the domain symmetric around zero', () => {
    const metrics = [makeMetric([8, 9], { inverse: true })]

    const [yMin, yMax] = composedValueDomain(metrics, compose(metrics))

    expect(yMin).toBe(-yMax)
    expect(yMax).toBeGreaterThan(0)
  })
})

describe('createM4CacheStore', () => {
  test('reuses the decimation while the metrics and their range are unchanged', () => {
    const store = createM4CacheStore(M4_BUCKETS)
    const metrics = [makeMetric([1, 2, 3])]

    expect(store.ensure(metrics, DATA_RANGE)).toBe(store.ensure(metrics, DATA_RANGE))
  })

  test('re-decimates when the metrics change', () => {
    const store = createM4CacheStore(M4_BUCKETS)
    const first = store.ensure([makeMetric([1, 2, 3])], DATA_RANGE)

    expect(store.ensure([makeMetric([4, 5, 6])], DATA_RANGE)).not.toBe(first)
  })

  test('re-decimates when the same metrics are placed on another range', () => {
    const store = createM4CacheStore(M4_BUCKETS)
    const metrics = [makeMetric([1, 2, 3])]
    const first = store.ensure(metrics, DATA_RANGE)

    expect(store.ensure(metrics, { start: 500, end: 600, step: STEP })).not.toBe(first)
  })
})
