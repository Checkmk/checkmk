/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { trendChartMetrics } from '@/dashboard/components/DashboardContent/NetworkFlow/trendChartMetrics'

const SERIES = [
  { name: 'HTTP', dataPoints: [1, 2] },
  { name: 'TLS', dataPoints: [3, 4] }
]

test('stacked areas share one stack, lines have none', () => {
  const stacked = trendChartMetrics(SERIES, 'stacked_area').map((m) => m.render.stack)
  const lines = trendChartMetrics(SERIES, 'lines').map((m) => m.render.stack)

  expect(new Set(stacked).size).toBe(1)
  expect(lines).toEqual([null, null])
})

test('series keep their rank order and get distinct throughput-formatted colors', () => {
  const metrics = trendChartMetrics(SERIES, 'lines')

  expect(metrics.map((m) => m.metadata.title)).toEqual(['HTTP', 'TLS'])
  expect(metrics[0]!.metadata.color).not.toBe(metrics[1]!.metadata.color)
  expect(metrics[0]!.metadata.unit.symbol).toBe('bps')
})
