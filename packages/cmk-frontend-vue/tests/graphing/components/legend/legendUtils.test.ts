/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import { metricStats } from '@/graphing/components/legend/legendUtils'

const UNIT: Metric['metadata']['unit'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

function makeMetric(dataPoints: (number | null)[]): Metric {
  return {
    metadata: { name: 'util', title: 'Utilization', unit: UNIT, color: '#ff0000' },
    render: { stack: null, inverse: false, hidden: false },
    data_points: dataPoints
  }
}

function renderedAlone(value: number): string {
  return metricStats(makeMetric([value])).last
}

test('last reports the final sample of a series ending in a value', () => {
  const finalSample = 2

  const stats = metricStats(makeMetric([3, 1, finalSample]))

  expect(stats.last).toBe(renderedAlone(finalSample))
})

test('last reports the final present sample of a series ending in a gap', () => {
  const finalSample = 2

  const stats = metricStats(makeMetric([3, 1, finalSample, null]))

  expect(stats.last).toBe(renderedAlone(finalSample))
})
