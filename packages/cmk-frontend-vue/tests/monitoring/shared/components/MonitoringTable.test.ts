/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'

interface Row {
  id: string
  name: string
  state: number
}

const COLUMNS: ColumnDef<Row>[] = [
  { id: 'name', accessorKey: 'name', header: 'Name', enableSorting: true },
  { id: 'state', accessorKey: 'state', header: 'State', enableSorting: true },
  { id: 'actions', header: 'Actions', enableSorting: false }
]

function makeRows(count: number): Row[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `row-${i}`,
    name: `host-${i}`,
    state: i % 3
  }))
}

function mountTable(overrides: {
  rows?: Row[]
  loading?: boolean
  sortState?: SortingState
  filterState?: ColumnFiltersState
  onSortUpdate?: (value: SortingState) => void
  onFilterUpdate?: (value: ColumnFiltersState) => void
  getRowKey?: (row: Row, index: number) => string | number
}) {
  const rows = overrides.rows ?? makeRows(3)
  const loading = overrides.loading ?? false
  const sortState = overrides.sortState ?? []
  const filterState = overrides.filterState ?? []
  const onSortUpdate = overrides.onSortUpdate ?? (() => {})
  const onFilterUpdate = overrides.onFilterUpdate ?? (() => {})
  const getRowKey = overrides.getRowKey

  return render(
    defineComponent({
      components: { MonitoringTable },
      setup() {
        return { rows, loading, sortState, filterState, onSortUpdate, onFilterUpdate, getRowKey }
      },
      render() {
        return h(
          MonitoringTable<Row>,
          {
            rows: this.rows,
            loading: this.loading,
            columns: COLUMNS,
            sortState: this.sortState,
            filterState: this.filterState,
            ...(this.getRowKey ? { getRowKey: this.getRowKey } : {}),
            'onUpdate:sortState': this.onSortUpdate,
            'onUpdate:filterState': this.onFilterUpdate
          },
          {
            row: ({ row, index }: { row: Row; index: number }) =>
              h('td', { 'data-testid': `row-${row.id}` }, `${index}:${row.name}`)
          }
        )
      }
    })
  )
}

test('renders all columns in the header', () => {
  mountTable({})

  expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'State' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Actions' })).toBeInTheDocument()
})

test('renders one row per item via the row slot', () => {
  mountTable({ rows: makeRows(3) })

  expect(screen.getByTestId('row-row-0')).toHaveTextContent('0:host-0')
  expect(screen.getByTestId('row-row-1')).toHaveTextContent('1:host-1')
  expect(screen.getByTestId('row-row-2')).toHaveTextContent('2:host-2')
})

test('sortable headers render as buttons; non-sortable headers do not', () => {
  mountTable({})

  expect(screen.getByRole('button', { name: 'Name' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'State' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Actions' })).not.toBeInTheDocument()
})

test('clicking a sortable header emits update:sortState with the new sort', async () => {
  const onSortUpdate = vi.fn()
  mountTable({ onSortUpdate })

  await fireEvent.click(screen.getByRole('button', { name: 'Name' }))

  expect(onSortUpdate).toHaveBeenCalledTimes(1)
  const next = onSortUpdate.mock.calls[0]![0] as SortingState
  expect(next).toEqual([{ id: 'name', desc: false }])
})

test('aria-sort reflects the active sort direction', () => {
  mountTable({ sortState: [{ id: 'state', desc: true }] })

  expect(screen.getByRole('columnheader', { name: 'State' })).toHaveAttribute(
    'aria-sort',
    'descending'
  )
  expect(screen.getByRole('columnheader', { name: 'Name' })).toHaveAttribute('aria-sort', 'none')
})

test('aria-busy is true when loading', () => {
  const { container } = mountTable({ loading: true })

  expect(container.querySelector('.monitoring-table')).toHaveAttribute('aria-busy', 'true')
})

test('aria-busy is false when not loading', () => {
  const { container } = mountTable({ loading: false })

  expect(container.querySelector('.monitoring-table')).toHaveAttribute('aria-busy', 'false')
})

test('uses getRowKey for row keying when provided', () => {
  mountTable({
    rows: makeRows(2),
    getRowKey: (row) => row.id
  })

  expect(screen.getByTestId('row-row-0')).toBeInTheDocument()
  expect(screen.getByTestId('row-row-1')).toBeInTheDocument()
})
