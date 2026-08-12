/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import AppearanceTable from '@/graphing/designer/components/AppearanceTable.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import type { DesignerItem } from '@/graphing/designer/drafts'
import type { ItemId } from '@/graphing/designer/types'

import { rrdMetricItem, rrdQueryItem } from '../fixtures'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

function metric(name: string, points: (number | null)[], color = '#123456'): Metric {
  return {
    metadata: {
      name,
      title: name,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: false
      },
      color
    },
    render: { stack: null, inverse: false, hidden: false },
    data_points: points
  }
}

function renderTable(
  seed: DesignerItem[],
  metricsBySource: Map<ItemId, Metric[]>,
  groupTitlesBySource: Map<ItemId, string> = new Map()
) {
  const store = useGraphItems(PALETTE)
  store.replaceAll(seed)
  return {
    store,
    ...render(AppearanceTable, { props: { store, metricsBySource, groupTitlesBySource } })
  }
}

test('shows the stats of rows that map to exactly one series', () => {
  renderTable(
    [rrdMetricItem('A'), rrdQueryItem('B')],
    new Map([
      ['A', [metric('a', [10, 30, 20])]],
      ['B', [metric('b1', [1]), metric('b2', [2])]]
    ])
  )
  // min, avg, max, last of row A
  expect(screen.getByText('10')).toBeInTheDocument()
  expect(screen.getAllByText('20')).not.toHaveLength(0)
  expect(screen.getByText('30')).toBeInTheDocument()
  // Row B fans into two series: no row-level stats.
  expect(screen.queryByText('1')).not.toBeInTheDocument()
  expect(screen.queryByText('2')).not.toBeInTheDocument()
})

test('shows the source type and title of every row', () => {
  renderTable([rrdMetricItem('A', { title: 'CPU load' }), rrdQueryItem('B')], new Map())
  expect(screen.getByText('CPU load')).toBeInTheDocument()
  expect(screen.getAllByText('Checkmk RRD')).toHaveLength(2)
})

test('resolves a single-line row title to its series title', () => {
  renderTable(
    [rrdMetricItem('A', { title: '$DEFAULT_TITLE$' })],
    new Map([['A', [metric('Resolved CPU', [5])]]])
  )
  expect(screen.getByText('Resolved CPU')).toBeInTheDocument()
  expect(screen.queryByText('$DEFAULT_TITLE$')).not.toBeInTheDocument()
})

test('falls back to the stored title when a single-line row has no series', () => {
  renderTable([rrdMetricItem('A', { title: 'Custom raw title' })], new Map())
  expect(screen.getByText('Custom raw title')).toBeInTheDocument()
})

test('shows the resolved group title for a multi-line row when provided', () => {
  renderTable(
    [rrdQueryItem('B', { title: '$DEFAULT_TITLE$' })],
    new Map(),
    new Map([['B', 'CPU load - <HOST_NAME>/<SERVICE_DESCRIPTION>']])
  )
  expect(screen.getByText('CPU load - <HOST_NAME>/<SERVICE_DESCRIPTION>')).toBeInTheDocument()
  expect(screen.queryByText('$DEFAULT_TITLE$')).not.toBeInTheDocument()
})

test('expands a multi-line row into one legend-styled row per resolved line', async () => {
  const { container } = renderTable(
    [rrdQueryItem('B', { title: 'Query B' })],
    new Map([
      ['B', [metric('line one', [10, 20], '#ff0000'), metric('line two', [30, 40], '#00ff00')]]
    ])
  )

  expect(screen.getByText('Query B')).toBeInTheDocument()
  expect(screen.queryByText('line one')).not.toBeInTheDocument()
  expect(screen.queryByText('10')).not.toBeInTheDocument()

  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))

  const rows = container.querySelectorAll('.graphing-appearance-table__expanded-row')
  expect(rows).toHaveLength(2)
  expect(rows[0]).toHaveTextContent('line one')
  expect(rows[1]).toHaveTextContent('line two')

  // Each line renders its own [min, avg, max, last]: line one [10,20], line two [30,40].
  expect(screen.getByText('10')).toBeInTheDocument() // line one min
  expect(screen.getByText('15')).toBeInTheDocument() // line one avg
  expect(screen.getAllByText('20')).toHaveLength(2) // line one max + last
  expect(screen.getByText('30')).toBeInTheDocument() // line two min
  expect(screen.getByText('35')).toBeInTheDocument() // line two avg
  expect(screen.getAllByText('40')).toHaveLength(2) // line two max + last

  const swatches = container.querySelectorAll('.graphing-appearance-table__color-swatch')
  expect(swatches).toHaveLength(2)
  expect(swatches[0]!.getAttribute('style')).toMatch(/#ff0000|rgb\(255, 0, 0\)/)
  expect(swatches[1]!.getAttribute('style')).toMatch(/#00ff00|rgb\(0, 255, 0\)/)
})

test('collapsing an expanded multi-line row hides its per-line rows again', async () => {
  renderTable(
    [rrdQueryItem('B', { title: 'Query B' })],
    new Map([['B', [metric('line one', [10, 20]), metric('line two', [30, 40])]]])
  )

  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))
  expect(screen.getByText('line one')).toBeInTheDocument()

  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))
  expect(screen.queryByText('line one')).not.toBeInTheDocument()
  expect(screen.queryByText('line two')).not.toBeInTheDocument()
})
