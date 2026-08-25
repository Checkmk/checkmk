/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { nextTick } from 'vue'

import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import AppearanceTable from '@/graphing/designer/components/AppearanceTable.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import type { DesignerItem } from '@/graphing/designer/drafts'
import type { ItemId } from '@/graphing/designer/types'

import { metricBackendItem, rrdMetricItem, rrdQueryItem } from '../fixtures'

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

function backendMetric(name: string): Metric {
  const base = metric(name, [1])
  return {
    ...base,
    metadata: {
      ...base.metadata,
      attributes: [
        { kind: 'resource', name: 'host.arch', value: 'x64' },
        { kind: 'data_point', name: 'status', value: '304' }
      ]
    }
  }
}

function renderTable(
  seed: DesignerItem[],
  metricsBySource: Map<ItemId, Metric[]>,
  resolvedTitles: Map<ItemId, string> = new Map()
) {
  const store = useGraphItems(PALETTE)
  store.replaceAll(seed)
  return {
    store,
    ...render(AppearanceTable, { props: { store, metricsBySource, resolvedTitles } })
  }
}

function toggles(): HTMLElement[] {
  return screen.getAllByRole('button', { name: 'Toggle details' })
}

/** The [min, avg, max, last] cells that close every row. */
function statsOf(row: HTMLElement): string[] {
  return [...row.querySelectorAll('td')].slice(-4).map((cell) => cell.textContent!.trim())
}

function rowOf(title: string): HTMLElement {
  return screen.getByText(title).closest('tr')!
}

test('shows the stats of rows that map to exactly one series', () => {
  renderTable(
    [rrdMetricItem('A', { title: 'Single' }), rrdQueryItem('B', { title: 'Fanned' })],
    new Map([
      ['A', [metric('a', [10, 30, 20])]],
      ['B', [metric('b1', [1]), metric('b2', [2])]]
    ])
  )
  expect(statsOf(rowOf('Single'))).toEqual(['10', '20', '30', '20'])
  // Row B fans into two series, so its own row attributes none of them.
  expect(statsOf(rowOf('Fanned'))).toEqual(['', '', '', ''])
})

test('opens the rows that fan out into lines, leaving single-line rows without a toggle', () => {
  renderTable(
    [rrdMetricItem('A', { title: 'Single' }), rrdQueryItem('B', { title: 'Fanned' })],
    new Map([
      ['A', [metric('a', [10])]],
      ['B', [metric('b1', [1]), metric('b2', [2])]]
    ])
  )

  expect(toggles()).toHaveLength(1)
  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'true')
})

test('a row reusing the id of a collapsed row starts expanded again', async () => {
  const { store } = renderTable(
    [rrdQueryItem('A', { title: 'Query A' })],
    new Map([['A', [metric('a1', [1]), metric('a2', [2])]]])
  )

  await fireEvent.click(toggles()[0]!)
  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'false')

  store.remove('A')
  await nextTick()
  store.addItem((id) => rrdQueryItem(id, { title: 'Query A again' }))
  await nextTick()

  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'true')
})

test('shows the source type and title of every row', () => {
  renderTable([rrdMetricItem('A', { title: 'CPU load' }), rrdQueryItem('B')], new Map())
  expect(screen.getByText('CPU load')).toBeInTheDocument()
  expect(screen.getAllByText('Checkmk RRD')).toHaveLength(2)
})

test('names every row by its resolved title, single-line and group alike', () => {
  renderTable(
    [
      rrdMetricItem('A', { title: '$DEFAULT_TITLE$' }),
      rrdQueryItem('B', { title: '$DEFAULT_TITLE$' })
    ],
    new Map(),
    new Map([
      ['A', 'Resolved CPU'],
      ['B', 'CPU load - <HOST_NAME>/<SERVICE_DESCRIPTION>']
    ])
  )
  expect(screen.getByText('Resolved CPU')).toBeInTheDocument()
  expect(screen.getByText('CPU load - <HOST_NAME>/<SERVICE_DESCRIPTION>')).toBeInTheDocument()
  expect(screen.queryByText('$DEFAULT_TITLE$')).not.toBeInTheDocument()
})

test('lists a multi-line row as one legend-styled row per resolved line', () => {
  const { container } = renderTable(
    [rrdQueryItem('B', { title: 'Query B' })],
    new Map([
      ['B', [metric('line one', [10, 20], '#ff0000'), metric('line two', [30, 40], '#00ff00')]]
    ])
  )

  expect(screen.getByText('Query B')).toBeInTheDocument()

  // Legend order, so the last line drawn heads the list.
  const rows = container.querySelectorAll('.graphing-appearance-table__expanded-row')
  expect(rows).toHaveLength(2)
  expect(rows[0]).toHaveTextContent('line two')
  expect(rows[1]).toHaveTextContent('line one')

  // Each line renders its own [min, avg, max, last]: line one [10,20], line two [30,40].
  expect(screen.getByText('10')).toBeInTheDocument() // line one min
  expect(screen.getByText('15')).toBeInTheDocument() // line one avg
  expect(screen.getAllByText('20')).toHaveLength(2) // line one max + last
  expect(screen.getByText('30')).toBeInTheDocument() // line two min
  expect(screen.getByText('35')).toBeInTheDocument() // line two avg
  expect(screen.getAllByText('40')).toHaveLength(2) // line two max + last

  const swatches = container.querySelectorAll('.graphing-appearance-table__color-swatch')
  expect(swatches).toHaveLength(2)
  expect(swatches[0]!.getAttribute('style')).toMatch(/#00ff00|rgb\(0, 255, 0\)/)
  expect(swatches[1]!.getAttribute('style')).toMatch(/#ff0000|rgb\(255, 0, 0\)/)
})

test('a resolved metrics-backend series expands into its attribute table', async () => {
  renderTable(
    [metricBackendItem('B', { title: 'Latency' })],
    new Map([['B', [backendMetric('line one')]]])
  )

  expect(screen.getByText('line one')).toBeInTheDocument()
  expect(screen.queryByText('host.arch')).not.toBeInTheDocument()

  // [0] is the source row, open from the start; [1] is its series.
  await fireEvent.click(toggles()[1]!)

  expect(screen.getByText('Attribute name')).toBeInTheDocument()
  const archRow = screen.getByText('host.arch').closest('tr')!
  expect(archRow).toHaveTextContent('x64')
  expect(archRow).toHaveTextContent('Resource')
})

// Names are unique per response, so this pins the invariant, not a reachable collision.
test('expanding a series leaves the same-named series of another source row collapsed', async () => {
  renderTable(
    [
      metricBackendItem('A', { title: 'Latency A' }),
      metricBackendItem('B', { title: 'Latency B' })
    ],
    new Map([
      ['A', [backendMetric('shared')]],
      ['B', [backendMetric('shared')]]
    ])
  )

  // Both source rows are open from the start; only A's series gets expanded.
  await fireEvent.click(toggles()[1]!)

  expect(screen.getAllByText('host.arch')).toHaveLength(1)
})

test('a series that loses its attributes while expanded leaves no table behind', async () => {
  const metricsBySource = new Map([['B', [backendMetric('line one')]]])
  const { rerender, store } = renderTable(
    [metricBackendItem('B', { title: 'Latency' })],
    metricsBySource
  )

  await fireEvent.click(toggles()[1]!)
  expect(screen.getByText('host.arch')).toBeInTheDocument()

  await rerender({
    store,
    metricsBySource: new Map([['B', [metric('line one', [1])]]]),
    resolvedTitles: new Map()
  })

  expect(screen.queryByText('Attribute name')).not.toBeInTheDocument()
})

test('collapsing a multi-line row hides its per-line rows, reopening brings them back', async () => {
  renderTable(
    [rrdQueryItem('B', { title: 'Query B' })],
    new Map([['B', [metric('line one', [10, 20]), metric('line two', [30, 40])]]])
  )

  await fireEvent.click(toggles()[0]!)
  expect(screen.queryByText('line one')).not.toBeInTheDocument()
  expect(screen.queryByText('line two')).not.toBeInTheDocument()

  await fireEvent.click(toggles()[0]!)
  expect(screen.getByText('line one')).toBeInTheDocument()
  expect(screen.getByText('line two')).toBeInTheDocument()
})

test('a row states its source, telling RRD and metrics backend rows apart', () => {
  renderTable(
    [rrdMetricItem('A', { title: 'From RRD' }), metricBackendItem('B', { title: 'From backend' })],
    new Map()
  )

  expect(screen.getByText('Checkmk RRD')).toBeInTheDocument()
  expect(screen.getByText('Metrics backend')).toBeInTheDocument()
})

test('per-row colour and visibility changes leave the other row untouched', async () => {
  const { store } = renderTable(
    [
      rrdMetricItem('A', { title: 'First', color: '#111111' }),
      rrdMetricItem('B', { title: 'Second', color: '#222222' })
    ],
    new Map()
  )

  const colorInput = rowOf('First').querySelector<HTMLInputElement>('input[type=color]')!
  await fireEvent.update(colorInput, '#ff0000')
  await fireEvent.click(within(rowOf('Second')).getByRole('button', { name: 'Toggle visibility' }))

  expect(store.items.value[0]).toMatchObject({ color: '#ff0000', visible: true })
  expect(store.items.value[1]).toMatchObject({ color: '#222222', visible: false })
})
