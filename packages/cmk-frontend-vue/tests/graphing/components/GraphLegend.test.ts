/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import GraphLegend from '@/graphing/components/GraphLegend.vue'
import type { HorizontalLine, Metric, UnitFormat } from '@/graphing/components/TimeSeriesGraph'

const UNIT: UnitFormat = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 }
}

function makeMetric(name: string, title: string, dataPoints: (number | null)[]): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000', expression: '' },
    render: { stack: 'area', inverse: false },
    data_points: dataPoints
  }
}

const CPU = makeMetric('cpu', 'CPU', [10, 20, 30])
const MEM = makeMetric('mem', 'Memory', [100, 200, 300])

test('renders one row per metric', () => {
  render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  expect(screen.getByText('CPU')).toBeInTheDocument()
  expect(screen.getByText('Memory')).toBeInTheDocument()
})

test('with fewer than 10 metrics, count is shown as non-interactive text', () => {
  render(GraphLegend, { props: { metrics: [CPU] } })
  expect(screen.getByText(/1 metric/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /1 metric/ })).not.toBeInTheDocument()
})

test('with 10 or more metrics, count is a button that emits requestShowAll', async () => {
  const metrics = Array.from({ length: 10 }, (_, i) => makeMetric(`m${i}`, `Metric ${i}`, [i]))
  const { emitted } = render(GraphLegend, { props: { metrics } })
  await fireEvent.click(screen.getByRole('button', { name: /10 metrics/ }))
  expect(emitted()).toHaveProperty('requestShowAll')
})

test('clicking a visible metric eye emits update:hiddenMetricNames with that name added', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: [] }
  })
  const cpuRow = screen.getByText('CPU').closest('tr')!
  await fireEvent.click(cpuRow.querySelector('button')!)
  expect(emitted()['update:hiddenMetricNames']).toEqual([[['cpu']]])
})

test('clicking a hidden metric eye emits update:hiddenMetricNames with that name removed', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU], hiddenMetricNames: ['cpu'] }
  })
  const cpuRow = screen.getByText('CPU').closest('tr')!
  await fireEvent.click(cpuRow.querySelector('button')!)
  expect(emitted()['update:hiddenMetricNames']).toEqual([[[]]])
})

test('hovering a metric row emits hoverMetric with the name, mouseleave emits null', async () => {
  const { emitted } = render(GraphLegend, { props: { metrics: [CPU] } })
  const row = screen.getByText('CPU').closest('tr')!
  await fireEvent.mouseEnter(row)
  await fireEvent.mouseLeave(row)
  expect(emitted()['hoverMetric']).toEqual([['cpu'], [null]])
})

test('horizontal lines render with their name and value', () => {
  const line: HorizontalLine = { name: 'Warning', value: 80, color: '#ffaa00' }
  render(GraphLegend, { props: { metrics: [CPU], horizontalLines: [line] } })
  expect(screen.getByText('Warning')).toBeInTheDocument()
  const warningRow = screen.getByText('Warning').closest('tr')!
  expect(warningRow).toHaveTextContent('80')
})

test('clicking a horizontal line eye emits update:hiddenLineNames with that name added', async () => {
  const line: HorizontalLine = { name: 'Warning', value: 80, color: '#ffaa00' }
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU], horizontalLines: [line], hiddenLineNames: [] }
  })
  const warningRow = screen.getByText('Warning').closest('tr')!
  await fireEvent.click(warningRow.querySelector('button')!)
  expect(emitted()['update:hiddenLineNames']).toEqual([[['Warning']]])
})

test('clicking a hidden horizontal line eye emits update:hiddenLineNames with that name removed', async () => {
  const line: HorizontalLine = { name: 'Warning', value: 80, color: '#ffaa00' }
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU], horizontalLines: [line], hiddenLineNames: ['Warning'] }
  })
  const warningRow = screen.getByText('Warning').closest('tr')!
  await fireEvent.click(warningRow.querySelector('button')!)
  expect(emitted()['update:hiddenLineNames']).toEqual([[[]]])
})
