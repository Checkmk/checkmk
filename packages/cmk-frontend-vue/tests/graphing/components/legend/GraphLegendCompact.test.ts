/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import type { HorizontalLine, Metric } from '@/graphing/components/TimeSeriesGraph'
import GraphLegendCompact from '@/graphing/components/legend/GraphLegendCompact.vue'

const LINE_UNIT: HorizontalLine['unit'] = {
  notation: 'decimal',
  symbol: '%',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const UNIT: Metric['metadata']['unit'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

function makeMetric(name: string, title: string): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000' },
    render: { stack: 'area', inverse: false, hidden: false },
    data_points: [10, 20, 30]
  }
}

function makeMetricWithStack(name: string, title: string, stack: string | null): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000' },
    render: { stack, inverse: false, hidden: false },
    data_points: [1]
  }
}

const CPU = makeMetric('cpu', 'CPU')
const MEM = makeMetric('mem', 'Memory')
const WARN_LINE: HorizontalLine = {
  name: 'scalar_of(warning,rrd_metric(h/svc/util))',
  title: 'Warn',
  value: 80,
  unit: LINE_UNIT,
  color: '#ffaa00'
}

test('renders one item per metric and per horizontal line', () => {
  render(GraphLegendCompact, { props: { metrics: [CPU, MEM], horizontalLines: [WARN_LINE] } })

  expect(screen.getByText('CPU')).toBeInTheDocument()
  expect(screen.getByText('Memory')).toBeInTheDocument()
  expect(screen.getByText('Warn')).toBeInTheDocument()
})

test('lists stacked metrics in the same top-to-bottom display order as the table legend', () => {
  const metrics = [
    makeMetricWithStack('a', 'A', null),
    makeMetricWithStack('b', 'B', 's1'),
    makeMetricWithStack('c', 'C', 's1'),
    makeMetricWithStack('d', 'D', 's1'),
    makeMetricWithStack('e', 'E', null),
    makeMetricWithStack('f', 'F', 's2'),
    makeMetricWithStack('g', 'G', 's2')
  ]

  const { container } = render(GraphLegendCompact, { props: { metrics } })

  const names = Array.from(container.querySelectorAll('.graphing-graph-legend-compact__name')).map(
    (el) => el.textContent
  )
  expect(names).toEqual(['A', 'D', 'C', 'B', 'E', 'G', 'F'])
})

test('long names are split into a shrinkable head and a fixed tail', () => {
  const { container } = render(GraphLegendCompact, {
    props: { metrics: [makeMetric('cpu', 'Total CPU utilization user')] }
  })

  const head = container.querySelector('.graphing-graph-legend-compact__name-head')!
  const tail = container.querySelector('.graphing-graph-legend-compact__name-tail')!
  expect(head.textContent! + tail.textContent!).toBe('Total CPU utilization user')
  expect(tail.textContent).toBe(' user')
})

test('the full name is available as the native title of the series', () => {
  render(GraphLegendCompact, {
    props: { metrics: [makeMetric('cpu', 'Total CPU utilization user')] }
  })

  expect(screen.getByTitle('Total CPU utilization user')).toBeInTheDocument()
})

test('clicking a visible metric eye emits update:hiddenMetricNames with that name added', async () => {
  const { emitted } = render(GraphLegendCompact, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: [] }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'CPU' }))

  expect(emitted()['update:hiddenMetricNames']).toEqual([[['cpu']]])
})

test('clicking a hidden metric eye emits update:hiddenMetricNames with that name removed', async () => {
  const { emitted } = render(GraphLegendCompact, {
    props: { metrics: [CPU], hiddenMetricNames: ['cpu'] }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'CPU' }))

  expect(emitted()['update:hiddenMetricNames']).toEqual([[[]]])
})

test('hovering a metric item emits hoverMetric with its name', async () => {
  const { emitted } = render(GraphLegendCompact, { props: { metrics: [CPU] } })
  const item = screen.getByText('CPU').closest('.graphing-graph-legend-compact__item')!

  await fireEvent.mouseEnter(item)

  expect(emitted()['hoverMetric']).toEqual([['cpu']])
})

test('leaving a metric item emits hoverMetric null', async () => {
  const { emitted } = render(GraphLegendCompact, { props: { metrics: [CPU] } })
  const item = screen.getByText('CPU').closest('.graphing-graph-legend-compact__item')!
  await fireEvent.mouseEnter(item)

  await fireEvent.mouseLeave(item)

  expect(emitted()['hoverMetric']).toEqual([['cpu'], [null]])
})

test('hovering a horizontal line item does not emit hoverMetric', async () => {
  const { emitted } = render(GraphLegendCompact, {
    props: { metrics: [CPU], horizontalLines: [WARN_LINE] }
  })
  const item = screen.getByText('Warn').closest('.graphing-graph-legend-compact__item')!

  await fireEvent.mouseEnter(item)
  await fireEvent.mouseLeave(item)

  expect(emitted()['hoverMetric']).toBeUndefined()
})

test('clicking a horizontal line eye emits update:hiddenLineNames with that name toggled', async () => {
  const { emitted } = render(GraphLegendCompact, {
    props: { metrics: [CPU], horizontalLines: [WARN_LINE], hiddenLineNames: [] }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'Warn' }))

  expect(emitted()['update:hiddenLineNames']).toEqual([
    [['scalar_of(warning,rrd_metric(h/svc/util))']]
  ])
})
