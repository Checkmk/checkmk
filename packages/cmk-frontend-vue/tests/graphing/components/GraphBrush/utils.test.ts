/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { computeSparklineBands, formatOverviewExtent } from '@/graphing/components/GraphBrush/utils'
import type { Metric, TimeRange } from '@/graphing/components/TimeSeriesGraph'

// computeSparklineBands only reads data_points, render.stack/inverse/hidden, and metadata.color.
function makeMetric(
  dataPoints: (number | null)[],
  options: { stack?: string | null; inverse?: boolean; color?: string; hidden?: boolean } = {}
): Metric {
  return {
    data_points: dataPoints,
    render: {
      stack: options.stack ?? null,
      inverse: options.inverse ?? false,
      hidden: options.hidden ?? false
    },
    metadata: { color: options.color ?? '#3366cc' }
  } as unknown as Metric
}

describe('formatOverviewExtent', () => {
  test('a multi-day extent shows the start and end dates', () => {
    const domain: TimeRange = { start: 1_700_000_000, end: 1_700_000_000 + 5 * 86_400, step: 60 }

    const label = formatOverviewExtent(domain, 'UTC')

    expect(label).toBe('2023-11-14 — 2023-11-19')
  })

  test('a same-day extent shows the date once with a start–end time range', () => {
    const start = 1_700_000_000
    const domain: TimeRange = { start, end: start + 3600, step: 60 }

    const label = formatOverviewExtent(domain, 'UTC')

    expect(label).toBe('2023-11-14 22:13–23:13')
  })
})

describe('computeSparklineBands', () => {
  test('reports no samples when the first metric has no data points', () => {
    const result = computeSparklineBands([makeMetric([])])

    expect(result.sampleCount).toBe(0)
    expect(result.bands).toEqual([])
  })

  test('an unstacked metric rests on the zero baseline', () => {
    const metrics = [makeMetric([10, 20])]

    const { bands, yMin, yMax } = computeSparklineBands(metrics)

    expect(bands[0]!.lower).toEqual([0, 0])
    expect(bands[0]!.upper).toEqual([10, 20])
    expect([yMin, yMax]).toEqual([0, 20])
  })

  test('metrics in the same stack group accumulate cumulatively', () => {
    const metrics = [makeMetric([10], { stack: 'g1' }), makeMetric([5], { stack: 'g1' })]

    const { bands, yMax } = computeSparklineBands(metrics)

    expect(bands[1]!.lower).toEqual([10])
    expect(bands[1]!.upper).toEqual([15])
    expect(yMax).toBe(15)
  })

  test('a hidden stack reference advances the stack base but draws no band of its own', () => {
    const metrics = [
      makeMetric([10], { stack: 'g1', hidden: true }),
      makeMetric([5], { stack: 'g1' })
    ]

    const { bands, yMax } = computeSparklineBands(metrics)

    expect(bands).toHaveLength(1)
    expect(bands[0]!.lower).toEqual([10])
    expect(bands[0]!.upper).toEqual([15])
    expect(yMax).toBe(15)
  })

  test('an inverse metric forces a symmetric y-domain around zero', () => {
    const metrics = [makeMetric([10], { inverse: true })]

    const { bands, yMin, yMax } = computeSparklineBands(metrics)

    expect(bands[0]!.upper).toEqual([-10])
    expect([yMin, yMax]).toEqual([-10, 10])
  })
})
