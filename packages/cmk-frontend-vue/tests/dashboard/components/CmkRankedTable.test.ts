/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable/CmkRankedTable.vue'
import type {
  RankedTableCell,
  RankedTableColumn,
  RankedTableRow
} from '@/dashboard/components/CmkRankedTable/types'

const COLUMNS: RankedTableColumn[] = [
  { key: 'host', title: 'Host', render: 'text', bar: false },
  { key: 'services', title: 'Services', render: 'count', bar: false },
  { key: 'problems', title: 'Problems', render: 'count', bar: true }
]

const ROWS: RankedTableRow[] = [
  { host: 'B', services: 5, problems: 100 },
  { host: 'A', services: 10, problems: 40 },
  { host: 'C', services: 1, problems: 20 }
]

const TWO_DESTINATIONS: RankedTableCell = {
  value: 'A',
  choices: [
    { title: 'Host', href: 'view.py?view_name=host' },
    { title: 'Services', href: 'view.py?view_name=host_services' }
  ]
}

function renderTable(rows: RankedTableRow[] = ROWS) {
  return render(CmkRankedTable, { props: { columns: COLUMNS, rows } })
}

test('renders a header per column and a row per data entry', () => {
  const { container } = renderTable()

  expect(container.querySelectorAll('.db-cmk-ranked-table__th')).toHaveLength(3)
  expect(container.querySelector('thead')).toHaveTextContent('Host')
  expect(container.querySelectorAll('tbody tr')).toHaveLength(3)
})

test('keeps the row order provided by the caller', () => {
  const { container } = renderTable()

  const firstCells = [...container.querySelectorAll('tbody tr')].map(
    (tr) => tr.querySelector('td')?.textContent
  )
  expect(firstCells).toEqual(['B', 'A', 'C'])
})

test('scales inline bars to the column max', () => {
  const { container } = renderTable()

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['100%', '40%', '20%'])
})

test('scales bars against a fixed barRange, clamped to it', () => {
  const columns: RankedTableColumn[] = [
    { key: 'host', title: 'Host', render: 'text', bar: false },
    { key: 'value', title: 'Value', render: 'count', bar: true, barRange: [100, 200] }
  ]
  const { container } = render(CmkRankedTable, {
    props: {
      columns,
      rows: [
        { host: 'A', value: 150 },
        { host: 'B', value: 40 },
        { host: 'C', value: 500 }
      ]
    }
  })

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['50%', '0%', '100%'])
})

test('fills the bar when the barRange has collapsed to a single value', () => {
  const columns: RankedTableColumn[] = [
    { key: 'host', title: 'Host', render: 'text', bar: false },
    { key: 'value', title: 'Value', render: 'count', bar: true, barRange: [42, 42] }
  ]
  const { container } = render(CmkRankedTable, {
    props: { columns, rows: [{ host: 'A', value: 42 }] }
  })

  const fill = container.querySelector<HTMLElement>('.db-cmk-ranked-table__bar-fill')
  expect(fill!.style.width).toBe('100%')
})

test("prefers a cell's formatted text over the column formatting", () => {
  const { container } = renderTable([
    { host: 'A', services: 1, problems: { value: 5, formatted: 'five' } }
  ])

  expect(container.querySelector('.db-cmk-ranked-table__bar-value')).toHaveTextContent('five')
})

test('lets a cell override the bar color', () => {
  const { container } = renderTable([
    { host: 'A', services: 1, problems: { value: 5, color: 'rgb(1, 2, 3)' } },
    { host: 'B', services: 1, problems: 2 }
  ])

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills[0]!.style.backgroundColor).toBe('rgb(1, 2, 3)')
  expect(fills[1]!.style.backgroundColor).toBe('var(--status-color-info)')
})

test('renders a link for cells carrying an href', () => {
  const { container } = renderTable([
    { host: { value: 'A', href: 'view.py?view_name=host' }, services: 1, problems: 5 }
  ])

  const link = container.querySelector<HTMLAnchorElement>('tbody a')
  expect(link).not.toBeNull()
  expect(link!.getAttribute('href')).toBe('view.py?view_name=host')
  expect(link!).toHaveTextContent('A')
})

test('offers the full text of truncatable cells as a tooltip, but not of figures', () => {
  const host = 'node_webshop_i-020818453318b7c7.eu-central-1.compute.internal'
  const { getByRole, queryByTitle } = renderTable([
    { host: { value: host, href: 'view.py' }, services: 1234, problems: 5 }
  ])

  expect(getByRole('link')).toHaveAttribute('title', host)
  expect(queryByTitle('1234')).toBeNull()
})

test('offers several destinations of a cell through a menu', () => {
  const { getByRole } = renderTable([
    {
      host: TWO_DESTINATIONS,
      services: 1,
      problems: 5
    }
  ])

  expect(getByRole('button', { name: 'A' })).toHaveAttribute('aria-haspopup', 'menu')
})

test('marks only a cell with several destinations with the menu arrow', () => {
  const { container } = renderTable([
    {
      host: TWO_DESTINATIONS,
      services: 1,
      problems: 5
    },
    { host: { value: 'B', href: 'view.py?view_name=host' }, services: 1, problems: 2 }
  ])

  const arrows = [...container.querySelectorAll('tbody tr')].map(
    (row) => row.querySelectorAll('.db-contextual-link-anchor__arrow').length
  )
  expect(arrows).toEqual([1, 0])
})

test('marks the table busy while new rows are fetched', () => {
  const { getByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, busy: true }
  })

  expect(getByRole('table')).toHaveAttribute('aria-busy', 'true')
})

test('shows as many loading rows as asked for, in place of the data', () => {
  const { getByRole, getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, placeholder: { kind: 'loading', rows: 5 } }
  })

  expect(getByRole('table')).toHaveAttribute('aria-busy', 'true')
  expect(getAllByRole('row').slice(1)).toHaveLength(5)
  expect(getByRole('table')).not.toHaveTextContent('B')
})

test('hides the faded stand-ins of an empty table but not its message', () => {
  const { queryByRole, getByText } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: [], placeholder: { kind: 'empty', rows: 3 } },
    slots: { empty: 'No data' }
  })

  expect(queryByRole('table')).toBeNull()
  expect(getByText('No data')).toBeVisible()
})

test('shows no stand-in rows for a negative row count', () => {
  const { getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: [], placeholder: { kind: 'loading', rows: -1 } }
  })

  expect(getAllByRole('row')).toHaveLength(1)
})

test('numbers the rows in the order provided, under a "Rank" header', () => {
  const { getByRole, getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, showRank: true }
  })

  expect(getByRole('columnheader', { name: 'Rank' })).toHaveTextContent('#')
  const ranks = getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelector('td')?.textContent?.trim())
  expect(ranks).toEqual(['1', '2', '3'])
})

test('shows no rank column unless asked for', () => {
  const { queryByRole } = renderTable()

  expect(queryByRole('columnheader', { name: 'Rank' })).toBeNull()
})

test('leaves the rank of loading rows blank', () => {
  const { getAllByRole } = render(CmkRankedTable, {
    props: {
      columns: COLUMNS,
      rows: ROWS,
      showRank: true,
      placeholder: { kind: 'loading', rows: 2 }
    }
  })

  const ranks = getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelector('td')?.textContent)
  expect(ranks).toEqual(['', ''])
})
