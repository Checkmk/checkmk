/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import KpiSparkLine from '@/dashboard/components/CmkKpiStatCard/KpiSparkLine.vue'
import type { TimestampedSample } from '@/dashboard/components/CmkKpiStatCard/types'

function sample(timestamp: number, value: number | null): TimestampedSample {
  return { timestamp, value }
}

function renderSparkLine(series: TimestampedSample[]) {
  return render(KpiSparkLine, { props: { series, color: 'var(--color-corporate-green-50)' } })
}

function linePathOf(container: Element): string {
  return (
    container.querySelector('.db-kpi-spark-line path[stroke="currentColor"]')?.getAttribute('d') ??
    ''
  )
}

test('positions samples by their timestamp, not by array index', () => {
  const { container: even } = renderSparkLine([sample(0, 0), sample(60, 10), sample(120, 20)])
  const { container: uneven } = renderSparkLine([sample(0, 0), sample(10, 10), sample(120, 20)])

  expect(linePathOf(even)).not.toBe(linePathOf(uneven))
})

test('breaks the line into separate subpaths at a null sample', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, null), sample(120, 20)])

  const pathData = linePathOf(container)
  expect(pathData.match(/M/g)?.length).toBeGreaterThan(1)
})

test('draws nothing for fewer than two non-null samples', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, null)])

  expect(linePathOf(container)).toBe('')
})
