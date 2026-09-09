/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  Row as TableRow,
  VisibilityState
} from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { type Ref, defineComponent, h, inject, nextTick, provide, ref } from 'vue'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import {
  COLUMN_LAYOUT_KEY,
  MONITORING_SERVICE
} from '@/monitoring/shared/components/MonitoringTableContext'
import type { FetchState, MonitoringService } from '@/monitoring/shared/services/MonitoringService'

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

/** The same table as {@link COLUMNS}, plus the column that turns row selection on. */
const COLUMNS_WITH_SELECT: ColumnDef<Row>[] = [
  { id: 'select', header: '', enableSorting: false, meta: { selectColumn: true } },
  ...COLUMNS
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
  onSortUpdate: (value: SortingState) => void = () => {},
  columnVisibility: Ref<VisibilityState> = ref({})
) {
  return {
    sortState: ref<SortingState>(sortState),
    updateSort: vi.fn((newSort: SortingState) => {
      onSortUpdate(newSort)
    }),
    columnVisibility,
    rowToReveal: ref<Row | null>(null),
    beginAutoPause: vi.fn(),
    endAutoPause: vi.fn()
  }
}

const layoutProbe = defineComponent({
  setup() {
    const columns = inject(COLUMN_LAYOUT_KEY, null)
    return () =>
      h('td', { 'data-testid': 'layout-probe' }, [...(columns?.value.keys() ?? [])].join(','))
  }
})

function probedLayout(): string {
  return screen.getAllByTestId('layout-probe')[0]!.textContent ?? ''
}

function mountTable(overrides: {
  rows?: Row[]
  columns?: ColumnDef<Row>[]
  fetchState?: FetchState
  hasLoaded?: boolean
  loadFailed?: boolean
  onRetry?: () => void
  sortState?: SortingState
  filterState?: ColumnFiltersState
  columnVisibility?: Ref<VisibilityState>
  onSortUpdate?: (value: SortingState) => void
  onFilterUpdate?: (value: ColumnFiltersState) => void
  getRowKey?: (row: Row, index: number) => string | number
}) {
  const rows = overrides.rows ?? makeRows(3)
  const columns = overrides.columns ?? COLUMNS
  const fetchState = overrides.fetchState ?? 'idle'
  const hasLoaded = overrides.hasLoaded ?? true
  const loadFailed = overrides.loadFailed ?? false
  const onRetry = overrides.onRetry ?? (() => {})
  const filterState = overrides.filterState ?? []
  const onFilterUpdate = overrides.onFilterUpdate ?? (() => {})
  const getRowKey = overrides.getRowKey
  const mockService = makeMockService(
    overrides.sortState,
    overrides.onSortUpdate,
    overrides.columnVisibility
  )

  return {
    mockService,
    ...render(
      defineComponent({
        components: { MonitoringTable },
        setup() {
          provide(MONITORING_SERVICE, mockService as unknown as MonitoringService<unknown>)
          return {
            rows,
            columns,
            fetchState,
            hasLoaded,
            loadFailed,
            onRetry,
            filterState,
            onFilterUpdate,
            getRowKey
          }
        },
        render() {
          return h(
            MonitoringTable<Row>,
            {
              rows: this.rows,
              fetchState: this.fetchState,
              hasLoaded: this.hasLoaded,
              loadFailed: this.loadFailed,
              columns: this.columns,
              filterState: this.filterState,
              ...(this.getRowKey ? { getRowKey: this.getRowKey } : {}),
              'onUpdate:filterState': this.onFilterUpdate,
              onRetry: this.onRetry
            },
            {
              row: ({
                row,
                index,
                tableRow
              }: {
                row: Row
                index: number
                tableRow: TableRow<Row>
              }) => [
                h('td', { 'data-testid': `row-${row.id}` }, `${index}:${row.name}`),
                h('td', { 'data-testid': `can-select-${row.id}` }, String(tableRow.getCanSelect())),
                h(layoutProbe)
              ],
              'empty-state': () => h('div', { 'data-testid': 'empty-state' }, 'nothing here')
            }
          )
        }
      })
    )
  }
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

async function pickSortDirection(column: string, direction: string): Promise<void> {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: `Filter ${column}` }))
  await user.click(screen.getByRole('button', { name: direction }))
}

test('the column panel sorts the column ascending', async () => {
  const onSortUpdate = vi.fn()
  mountTable({ onSortUpdate })

  await pickSortDirection('Name', 'Sort ascending')

  expect(onSortUpdate).toHaveBeenCalledTimes(1)
  expect(onSortUpdate.mock.calls[0]![0]).toEqual([{ id: 'name', desc: false }])
})

test('the column panel sorts the column descending', async () => {
  const onSortUpdate = vi.fn()
  mountTable({ onSortUpdate })

  await pickSortDirection('Name', 'Sort descending')

  expect(onSortUpdate).toHaveBeenCalledTimes(1)
  expect(onSortUpdate.mock.calls[0]![0]).toEqual([{ id: 'name', desc: true }])
})

test('the column panel drops only its own column out of a multi-column sort', async () => {
  const onSortUpdate = vi.fn()
  mountTable({
    sortState: [
      { id: 'name', desc: true },
      { id: 'state', desc: false }
    ],
    onSortUpdate
  })

  await pickSortDirection('Name', 'No sorting / default sorting')

  expect(onSortUpdate).toHaveBeenCalledTimes(1)
  expect(onSortUpdate.mock.calls[0]![0]).toEqual([{ id: 'state', desc: false }])
})

test('the column panel marks the direction the column is sorted by', async () => {
  const user = userEvent.setup()
  mountTable({ sortState: [{ id: 'name', desc: true }] })

  await user.click(screen.getByRole('button', { name: 'Filter Name' }))

  expect(screen.getByRole('button', { name: 'Sort descending' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.getByRole('button', { name: 'Sort ascending' })).toHaveAttribute(
    'aria-pressed',
    'false'
  )
})

test('aria-busy is true while a fetch is in flight', () => {
  const { container } = mountTable({ fetchState: 'background' })

  expect(container.querySelector('.monitoring-table')).toHaveAttribute('aria-busy', 'true')
})

test('aria-busy is false when idle', () => {
  const { container } = mountTable({ fetchState: 'idle' })

  expect(container.querySelector('.monitoring-table')).toHaveAttribute('aria-busy', 'false')
})

test('shows the skeleton on the initial load (foreground fetch before first settle)', () => {
  const { container } = mountTable({ rows: [], fetchState: 'foreground', hasLoaded: false })

  // The real table carries the monitoring-table__table class; the skeleton does not.
  expect(container.querySelector('.monitoring-table__table')).not.toBeInTheDocument()
})

test('keeps the table mounted during a background refresh after the first load', async () => {
  const { container } = mountTable({ rows: makeRows(3), fetchState: 'background', hasLoaded: true })
  await flushVirtualizer()

  // No skeleton swap: the existing table stays so the poll does not visibly rebuild it.
  expect(container.querySelector('.monitoring-table__table')).toBeInTheDocument()
  expect(screen.getByTestId('row-row-0')).toHaveTextContent('0:host-0')
})

test('keeps the empty state during a background refresh of an empty result', () => {
  // A result set that is genuinely empty must not flash back to the skeleton on
  // every poll — once loaded, the empty state stays put while the poll runs.
  const { container } = mountTable({ rows: [], fetchState: 'background', hasLoaded: true })

  expect(container.querySelector('.monitoring-table__table')).toBeInTheDocument()
  expect(screen.getByTestId('empty-state')).toBeInTheDocument()
})

test('shows the skeleton during a foreground reload (search/filter/sort) after the first load', () => {
  const { container } = mountTable({
    rows: makeRows(3),
    fetchState: 'foreground',
    hasLoaded: true
  })

  // A foreground reload swaps back to the skeleton, just like the initial load.
  expect(container.querySelector('.monitoring-table__table')).not.toBeInTheDocument()
})

test('does not flash the empty state during a foreground reload of a previously empty result', () => {
  const { container } = mountTable({
    rows: [],
    fetchState: 'foreground',
    hasLoaded: true
  })

  expect(container.querySelector('.monitoring-table__table')).not.toBeInTheDocument()
  expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
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

test('says the results could not be loaded when the fetch failed', () => {
  mountTable({ rows: [], hasLoaded: true, loadFailed: true })

  expect(screen.getByRole('alert')).toHaveTextContent('Could not load the results')
})

test('does not pass a failed fetch off as an empty result', () => {
  mountTable({ rows: [], hasLoaded: true, loadFailed: true })

  expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
})

test('offers a retry for a failed fetch', async () => {
  const onRetry = vi.fn()
  mountTable({ rows: [], hasLoaded: true, loadFailed: true, onRetry })

  await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

  expect(onRetry).toHaveBeenCalledOnce()
})

test('renders the empty-state slot when there are no rows and not loading', () => {
  mountTable({ rows: [] })

  expect(screen.getByTestId('empty-state')).toBeInTheDocument()
})

test('does not render the empty-state slot during the initial load', () => {
  mountTable({ rows: [], fetchState: 'foreground', hasLoaded: false })

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

test('keeps the filter buttons enabled in the empty state', () => {
  mountTable({ rows: [] })

  expect(screen.getByRole('button', { name: 'Filter Name' })).toBeEnabled()
  expect(screen.getByRole('button', { name: 'Filter State' })).toBeEnabled()
})

test('keeps the filter buttons enabled when there are rows', () => {
  mountTable({ rows: makeRows(3) })

  expect(screen.getByRole('button', { name: 'Filter Name' })).toBeEnabled()
})

test('hides a column the service marks invisible', () => {
  mountTable({ columnVisibility: ref({ state: false }) })

  expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument()
  expect(screen.queryByRole('columnheader', { name: 'State' })).not.toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Actions' })).toBeInTheDocument()
})

test('keeps a hidden column out of the provided column layout', async () => {
  mountTable({ columnVisibility: ref({ state: false }) })
  await flushVirtualizer()

  expect(probedLayout()).toBe('name,actions')
})

test('picks up a visibility change without a remount', async () => {
  const columnVisibility = ref<VisibilityState>({})
  mountTable({ columnVisibility })
  await flushVirtualizer()
  expect(probedLayout()).toBe('name,state,actions')

  columnVisibility.value = { name: false }
  await flushVirtualizer()

  expect(screen.queryByRole('columnheader', { name: 'Name' })).not.toBeInTheDocument()
  expect(probedLayout()).toBe('state,actions')
})

test('clicking a disabled header in the empty state does not sort', async () => {
  const onSortUpdate = vi.fn()
  mountTable({ rows: [], onSortUpdate })

  // userEvent honours the disabled attribute (a real click is suppressed),
  // unlike fireEvent which dispatches the event regardless.
  await userEvent.click(screen.getByRole('button', { name: 'Name' }))

  expect(onSortUpdate).not.toHaveBeenCalled()
})

test('consumes a reveal request for a row it lists', async () => {
  const rows = makeRows(3)
  const { mockService } = mountTable({ rows })
  await flushVirtualizer()

  mockService.rowToReveal.value = rows[2]!
  await flushVirtualizer()

  expect(mockService.rowToReveal.value).toBeNull()
})

test('consumes a reveal request for a row it does not list, rather than holding it', async () => {
  const { mockService } = mountTable({ rows: makeRows(3) })
  await flushVirtualizer()

  mockService.rowToReveal.value = { id: 'elsewhere', name: 'host-9', state: 0 }
  await flushVirtualizer()

  expect(mockService.rowToReveal.value).toBeNull()
})

/*
 * The select column is the switch for row selection: a table without it belongs to a user who may
 * run no command, and must not offer a selection at all - not even to a programmatic caller.
 */

test('offers no row selection while no column declares itself the select column', async () => {
  mountTable({})
  await flushVirtualizer()

  expect(screen.queryByRole('checkbox', { name: 'Select all rows' })).not.toBeInTheDocument()
  expect(screen.getByTestId('can-select-row-0')).toHaveTextContent('false')
})

test('offers row selection once a column declares itself the select column', async () => {
  mountTable({ columns: COLUMNS_WITH_SELECT })
  await flushVirtualizer()

  expect(screen.getByRole('checkbox', { name: 'Select all rows' })).toBeInTheDocument()
  expect(screen.getByTestId('can-select-row-0')).toHaveTextContent('true')
})

test('the select-all hit area carries a native tooltip, since the checkbox itself cannot', async () => {
  const { container } = mountTable({ columns: COLUMNS_WITH_SELECT })
  await flushVirtualizer()

  // The checkbox has `pointer-events: none` here (see .monitoring-table-header__select
  // :deep(.cmk-checkbox__container)), so a title on it would never be hovered.
  expect(container.querySelector('.monitoring-table-header__select')).toHaveAttribute(
    'title',
    'Select all rows'
  )
})
