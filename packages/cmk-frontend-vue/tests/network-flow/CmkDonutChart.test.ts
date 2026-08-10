/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import CmkDonutChart from '@/network-flow/CmkDonutChart/CmkDonutChart.vue'
import type { DonutSlice } from '@/network-flow/CmkDonutChart/types'

const SLICES: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 90, color: 'blue' },
  { key: 'other', label: 'Other', value: 60, color: 'grey' }
]

function renderChart(slices: DonutSlice[] = SLICES) {
  return render(CmkDonutChart, { props: { slices } })
}

test('renders one arc segment and one legend entry per slice', () => {
  const { container } = renderChart()

  expect(container.querySelectorAll('path')).toHaveLength(2)
  // The empty-track circle is only rendered when there are no slices.
  expect(container.querySelectorAll('circle')).toHaveLength(0)
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__legend-item')).toHaveLength(2)
})

test('derives percentages from the sum of all slice values', () => {
  const { container } = renderChart()

  const values = [...container.querySelectorAll('.network-flow-cmk-donut-chart__legend-value')].map(
    (el) => el.textContent
  )
  // 90 / 150 = 60%, 60 / 150 = 40%.
  expect(values).toEqual(['60.0%', '40.0%'])
})

test('highlights the top slice in the center', () => {
  const { container } = renderChart()

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '60.0%'
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'TLS'
  )
})

test('colors each arc segment with its slice color', () => {
  const { container } = renderChart()

  const fills = [...container.querySelectorAll<SVGPathElement>('path')].map((el) =>
    el.getAttribute('fill')
  )
  // The named colors resolve to their theme palette CSS variables.
  expect(fills).toEqual(['var(--color-light-blue-50)', 'var(--color-mid-grey-50)'])
})

test('draws a lone slice as a closed ring', () => {
  const { container } = renderChart([{ key: 'tls', label: 'TLS', value: 90, color: 'blue' }])

  // A closed ring is all arcs; the straight edges of a segment would show up
  // as line commands.
  expect(
    container.querySelector('.network-flow-cmk-donut-chart__slice')!.getAttribute('d')
  ).not.toContain('L')
})

test('renders an empty track and no center when there are no slices', () => {
  const { container } = renderChart([])

  expect(container.querySelectorAll('path')).toHaveLength(0)
  expect(container.querySelectorAll('circle')).toHaveLength(1)
  expect(container.querySelector('.network-flow-cmk-donut-chart__empty-track')).not.toBeNull()
  expect(container.querySelector('.network-flow-cmk-donut-chart__center')).toBeNull()
})
