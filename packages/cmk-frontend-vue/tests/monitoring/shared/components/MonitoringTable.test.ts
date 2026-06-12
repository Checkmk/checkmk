/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h, nextTick, provide, ref } from 'vue'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
})

afterAll(() => {
  if (originalOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  }
  if (originalOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
  }
})

interface Row {
  id: string
  name: string
  state: number
}

const COLUMNS: ColumnDef<Row>[] = [
  {
    id: 'name',
    accessorKey: 'name',
    header: 'Name',
    enableSorting: true,
    meta: { filter: { type: 'checkbox-list', field: 'name', options: [] } }
  },
  {
    id: 'state',
    accessorKey: 'state',
    header: 'State',
    enableSorting: true,
    meta: { filter: { type: 'checkbox-list', field: 'state', options: [] } }
  },
  { id: 'actions', header: 'Actions', enableSorting: false }
]

function makeRows(count: number): Row[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `row-${i}`,
    name: `host-${i}`,
    state: i % 3
  }))
}

function makeMockService(
  sortState: SortingState = [],
  onSortUpdate: (value: SortingState) => void = () => {}
) {
  return {
    sortState: ref<SortingState>(sortState),
    updateSort: vi.fn((newSort: SortingState) => {
      onSortUpdate(newSort)
    })
  }
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
  const filterState = overrides.filterState ?? []
  const onFilterUpdate = overrides.onFilterUpdate ?? (() => {})
  const getRowKey = overrides.getRowKey
  const mockService = makeMockService(overrides.sortState, overrides.onSortUpdate)

  return render(
    defineComponent({
      components: { MonitoringTable },
      setup() {
        provide(MONITORING_SERVICE, mockService as unknown as MonitoringService<unknown>)
        return { rows, loading, filterState, onFilterUpdate, getRowKey }
      },
      render() {
        return h(
          MonitoringTable<Row>,
          {
            rows: this.rows,
            loading: this.loading,
            columns: COLUMNS,
            filterState: this.filterState,
            ...(this.getRowKey ? { getRowKey: this.getRowKey } : {}),
            'onUpdate:filterState': this.onFilterUpdate
          },
          {
            row: ({ row, index }: { row: Row; index: number }) =>
              h('td', { 'data-testid': `row-${row.id}` }, `${index}:${row.name}`),
            'empty-state': () => h('div', { 'data-testid': 'empty-state' }, 'nothing here')
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

async function flushVirtualizer(): Promise<void> {
  await nextTick()
  await nextTick()
}

test('renders one row per item via the row slot', async () => {
  mountTable({ rows: makeRows(3) })
  await flushVirtualizer()

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

test('clicking a sortable header calls updateSort with the new sort', async () => {
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

test('uses getRowKey for row keying when provided', async () => {
  mountTable({
    rows: makeRows(2),
    getRowKey: (row) => row.id
  })
  await flushVirtualizer()

  expect(screen.getByTestId('row-row-0')).toBeInTheDocument()
  expect(screen.getByTestId('row-row-1')).toBeInTheDocument()
})

test('renders the empty-state slot when there are no rows and not loading', () => {
  mountTable({ rows: [] })

  expect(screen.getByTestId('empty-state')).toBeInTheDocument()
})

test('does not render the empty-state slot while loading', () => {
  mountTable({ rows: [], loading: true })

  expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
})

test('does not render the empty-state slot when there are rows', () => {
  mountTable({ rows: makeRows(3) })

  expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
})

test('disables the sort buttons in the empty state', () => {
  mountTable({ rows: [] })

  expect(screen.getByRole('button', { name: 'Name' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'State' })).toBeDisabled()
})

test('keeps the sort buttons enabled when there are rows', () => {
  mountTable({ rows: makeRows(3) })

  expect(screen.getByRole('button', { name: 'Name' })).toBeEnabled()
})

test('disables the filter buttons in the empty state', () => {
  mountTable({ rows: [] })

  expect(screen.getByRole('button', { name: 'Filter Name' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Filter State' })).toBeDisabled()
})

test('keeps the filter buttons enabled when there are rows', () => {
  mountTable({ rows: makeRows(3) })

  expect(screen.getByRole('button', { name: 'Filter Name' })).toBeEnabled()
})

test('clicking a disabled header in the empty state does not sort', async () => {
  const onSortUpdate = vi.fn()
  mountTable({ rows: [], onSortUpdate })

  // userEvent honours the disabled attribute (a real click is suppressed),
  // unlike fireEvent which dispatches the event regardless.
  await userEvent.click(screen.getByRole('button', { name: 'Name' }))

  expect(onSortUpdate).not.toHaveBeenCalled()
})
