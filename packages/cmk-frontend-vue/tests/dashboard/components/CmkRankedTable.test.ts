/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable/CmkRankedTable.vue'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable/types'

const COLUMNS: RankedTableColumn[] = [
  { key: 'host', title: 'Host', render: 'text', bar: false },
  { key: 'ingress', title: 'Ingress', render: 'bytes', bar: false },
  { key: 'volume', title: 'Volume', render: 'bytes', bar: true }
]

const ROWS: RankedTableRow[] = [
  { host: 'B', ingress: 5e9, volume: 100e9 },
  { host: 'A', ingress: 10e9, volume: 40e9 },
  { host: 'C', ingress: 1e9, volume: 20e9 }
]

function renderTable(rows: RankedTableRow[] = ROWS) {
  return render(CmkRankedTable, {
    props: { columns: COLUMNS, rows, barColor: 'green' as const }
  })
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

test('scales inline bars to the column max and fills them with the accent color', () => {
  const { container } = renderTable()

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['100%', '40%', '20%'])
  // The named color resolves to its theme palette CSS variable.
  expect(fills[0]!.style.backgroundColor).toBe('var(--color-corporate-green-50)')
})

test('emits cellClick with column and row when a clickable cell is activated', async () => {
  const clickableColumns: RankedTableColumn[] = [
    { key: 'host', title: 'Host', render: 'text', bar: false, clickable: true },
    { key: 'volume', title: 'Volume', render: 'bytes', bar: true }
  ]
  const { container, emitted } = render(CmkRankedTable, {
    props: { columns: clickableColumns, rows: ROWS, barColor: 'green' as const }
  })

  const button = container.querySelector<HTMLButtonElement>('.db-cmk-ranked-table__link')
  expect(button).not.toBeNull()
  await fireEvent.click(button!)

  const events = emitted()['cellClick'] as [RankedTableColumn, RankedTableRow][]
  expect(events).toHaveLength(1)
  expect(events[0]![0]!.key).toBe('host')
  expect(events[0]![1]!.host).toBe('B')
})

test('renders plain text (no button) for non-clickable columns', () => {
  const { container } = renderTable()

  expect(container.querySelector('.db-cmk-ranked-table__link')).toBeNull()
})

test('formats byte columns as human-readable SI values', () => {
  const { container } = renderTable([
    { host: 'A', ingress: 10e9, volume: 90.4e9 },
    { host: 'B', ingress: 5e9, volume: 552.63e6 }
  ])

  const barValues = [...container.querySelectorAll('.db-cmk-ranked-table__bar-value')].map(
    (el) => el.textContent
  )
  // Scaled to GB / MB (the SI formatter trims trailing zeros: 90.4, not 90.40).
  expect(barValues).toEqual(['90.4 GB', '552.63 MB'])
})
