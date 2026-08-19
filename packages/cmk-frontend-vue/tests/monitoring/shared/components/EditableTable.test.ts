/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, RowSelectionState, Row as TanStackRow } from '@tanstack/vue-table'
import { fireEvent, render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { defineComponent, h, ref } from 'vue'

import EditableTable from '@/monitoring/shared/components/EditableTable.vue'
import DragHandleCell from '@/monitoring/shared/components/cell/DragHandleCell.vue'

interface Row {
  id: string
  name: string
}

const COLUMNS: ColumnDef<Row>[] = [
  { id: 'drag', header: '' },
  { id: 'name', accessorKey: 'name', header: 'Name' }
]

function makeRows(count: number): Row[] {
  return Array.from({ length: count }, (_, i) => ({ id: `row-${i}`, name: `line-${i}` }))
}

function mountEditableTable(options: {
  rows?: Row[]
  columns?: ColumnDef<Row>[]
  expandedRows?: Record<string, boolean>
  rowHeight?: string
  onReorder?: (fromIndex: number, toIndex: number) => void
  withFooter?: boolean
  withEmptyState?: boolean
  getRowVariant?: (row: Row, index: number) => 'error' | null
}) {
  const rows = options.rows ?? makeRows(3)

  return render(
    defineComponent({
      render() {
        return h(
          EditableTable<Row>,
          {
            rows,
            columns: options.columns ?? COLUMNS,
            expandedRows: options.expandedRows ?? {},
            getRowKey: (row: Row) => row.id,
            ...(options.rowHeight ? { rowHeight: options.rowHeight } : {}),
            ...(options.onReorder ? { onReorder: options.onReorder } : {}),
            ...(options.getRowVariant ? { getRowVariant: options.getRowVariant } : {})
          },
          {
            row: ({ row, index }: { row: Row; index: number }) => [
              h(DragHandleCell, { columnId: 'drag' }),
              h('td', { 'data-testid': `row-${row.id}` }, `${index}:${row.name}`)
            ],
            expansion: ({ row }: { row: Row }) =>
              h(
                'tr',
                h(
                  'td',
                  { colspan: 2, 'data-testid': `expansion-${row.id}` },
                  `expanded:${row.name}`
                )
              ),
            ...(options.withFooter
              ? { footer: () => h('td', { colspan: 2, 'data-testid': 'footer-cell' }, 'Add') }
              : {}),
            ...(options.withEmptyState
              ? { 'empty-state': () => h('span', { 'data-testid': 'empty-state' }, 'No rows yet') }
              : {})
          }
        )
      }
    })
  )
}

function dragHandles(): HTMLElement[] {
  return screen.getAllByRole('button', { name: 'Drag to reorder' })
}

async function dragRow(handle: HTMLElement): Promise<void> {
  await fireEvent(handle, new MouseEvent('dragstart', { bubbles: true, clientY: 100 }))
  await fireEvent(handle, new MouseEvent('drag', { bubbles: true, clientY: 100 }))
  await fireEvent(handle, new MouseEvent('dragend', { bubbles: true, clientY: 100 }))
}

function moveRow(rows: Row[], fromIndex: number, toIndex: number): Row[] {
  const next = [...rows]
  const moved = next.splice(fromIndex, 1)[0]!
  next.splice(toIndex, 0, moved)
  return next
}

test('renders every row', () => {
  mountEditableTable({ rows: makeRows(60) })

  expect(screen.getByTestId('row-row-0')).toBeInTheDocument()
  expect(screen.getByTestId('row-row-59')).toBeInTheDocument()
})

test('marks the rows a variant calls erroring, and only those', () => {
  mountEditableTable({
    rows: makeRows(2),
    getRowVariant: (row: Row) => (row.id === 'row-1' ? 'error' : null)
  })

  expect(screen.getByTestId('row-row-1').closest('tr')).toHaveClass(
    'monitoring-editable-table__row--error'
  )
  expect(screen.getByTestId('row-row-0').closest('tr')).not.toHaveClass(
    'monitoring-editable-table__row--error'
  )
})

test('renders no sort buttons even when column definitions allow sorting', () => {
  mountEditableTable({})

  expect(screen.getByText('Name')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Name' })).not.toBeInTheDocument()
})

test('renders a markup help tooltip for a column declaring headerHelp', async () => {
  mountEditableTable({
    columns: [
      { id: 'drag', header: '' },
      {
        id: 'name',
        accessorKey: 'name',
        header: 'Name',
        meta: { headerHelp: untranslated('Line one<br>Line <tt>two</tt>') }
      }
    ]
  })

  await fireEvent.click(screen.getByRole('button', { name: 'Help for Name' }))

  const tooltip = await screen.findByRole('tooltip')
  // Markup survives sanitization: <br> renders as a real line break, macros as <tt> - not plain text.
  expect(tooltip.querySelector('br')).not.toBeNull()
  expect(screen.getByText('two').tagName).toBe('TT')
})

test('renders no help trigger for a column without headerHelp', () => {
  mountEditableTable({})

  expect(screen.queryByRole('button', { name: 'Help for Name' })).not.toBeInTheDocument()
})

test('renders the expansion slot only for expanded row keys', () => {
  mountEditableTable({ expandedRows: { 'row-1': true } })

  expect(screen.getByTestId('expansion-row-1')).toHaveTextContent('expanded:line-1')
  expect(screen.queryByTestId('expansion-row-0')).not.toBeInTheDocument()
  expect(screen.queryByTestId('expansion-row-2')).not.toBeInTheDocument()
})

test('renders the footer slot inside a tfoot', () => {
  const { container } = mountEditableTable({ withFooter: true })

  expect(container.querySelector('tfoot')).toContainElement(screen.getByTestId('footer-cell'))
})

test('renders the footer even when the table is empty', () => {
  mountEditableTable({ rows: [], withFooter: true })

  expect(screen.getByTestId('footer-cell')).toBeInTheDocument()
})

test('renders no tfoot without a footer slot', () => {
  const { container } = mountEditableTable({})

  expect(container.querySelector('tfoot')).not.toBeInTheDocument()
})

test('renders the empty-state slot when there are no rows', () => {
  mountEditableTable({ rows: [], withEmptyState: true })

  expect(screen.getByTestId('empty-state')).toBeInTheDocument()
})

test('renders no row body at all without an empty-state slot', () => {
  const { container } = mountEditableTable({ rows: [] })

  expect(container.querySelector('tbody')).not.toBeInTheDocument()
})

test('renders no empty state while rows exist', () => {
  mountEditableTable({ withEmptyState: true })

  expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
})

// jsdom has no layout: every row rect collapses to 0, so a positive clientY is
// "below" every row midpoint and dragging row 0 must target the last row.
test('dragging a row handle emits reorder with the traversed target index', async () => {
  const onReorder = vi.fn()
  mountEditableTable({ rows: makeRows(3), onReorder })

  await dragRow(dragHandles()[0]!)

  expect(onReorder).toHaveBeenCalledWith(0, 2)
})

test('keeps expansion rows in the DOM while a drag is in progress', async () => {
  mountEditableTable({ expandedRows: { 'row-1': true } })

  const handle = dragHandles()[0]!
  await fireEvent(handle, new MouseEvent('dragstart', { bubbles: true, clientY: 100 }))
  expect(screen.getByTestId('expansion-row-1')).toBeInTheDocument()

  await fireEvent(handle, new MouseEvent('dragend', { bubbles: true, clientY: 100 }))
  expect(screen.getByTestId('expansion-row-1')).toBeInTheDocument()
})

// Discriminating despite jsdom's zero rects: if the expansion row leaked into
// the drag index math, the traversal would target index 3 instead of 2.
test('emits data indices when a row below the dragged one is expanded', async () => {
  const onReorder = vi.fn()
  mountEditableTable({ rows: makeRows(3), expandedRows: { 'row-1': true }, onReorder })

  await dragRow(dragHandles()[0]!)

  expect(onReorder).toHaveBeenCalledWith(0, 2)
})

test('moves the expansion row with its data row when a reorder is applied', async () => {
  render(
    defineComponent({
      setup() {
        const rows = ref(makeRows(3))
        function onReorder(fromIndex: number, toIndex: number) {
          rows.value = moveRow(rows.value, fromIndex, toIndex)
        }
        return () =>
          h(
            EditableTable<Row>,
            {
              rows: rows.value,
              columns: COLUMNS,
              expandedRows: { 'row-1': true },
              getRowKey: (row: Row) => row.id,
              onReorder
            },
            {
              row: ({ row }: { row: Row }) => [
                h(DragHandleCell, { columnId: 'drag' }),
                h('td', { 'data-testid': `row-${row.id}` }, row.name)
              ],
              expansion: ({ row }: { row: Row }) =>
                h(
                  'tr',
                  h(
                    'td',
                    { colspan: 2, 'data-testid': `expansion-${row.id}` },
                    `expanded:${row.name}`
                  )
                )
            }
          )
      }
    })
  )

  await dragRow(dragHandles()[0]!)

  const expansionRow = screen.getByTestId('expansion-row-1').closest('tr')!
  expect(expansionRow.previousElementSibling).toContainElement(screen.getByTestId('row-row-1'))
})

test('keeps the selection on the same row through a reorder', async () => {
  const rowSelection = ref<RowSelectionState>({})
  const rows = ref(makeRows(3))

  render(
    defineComponent({
      setup() {
        function onReorder(fromIndex: number, toIndex: number) {
          rows.value = moveRow(rows.value, fromIndex, toIndex)
        }
        return () =>
          h(
            EditableTable<Row>,
            {
              rows: rows.value,
              columns: COLUMNS,
              rowSelection: rowSelection.value,
              'onUpdate:rowSelection': (value: RowSelectionState) => (rowSelection.value = value),
              getRowKey: (row: Row) => row.id,
              onReorder
            },
            {
              row: ({ row, tableRow }: { row: Row; tableRow: TanStackRow<Row> }) => [
                h(DragHandleCell, { columnId: 'drag' }),
                h('td', [
                  h('input', {
                    type: 'checkbox',
                    'data-testid': `select-${row.id}`,
                    checked: tableRow.getIsSelected(),
                    onChange: () => tableRow.toggleSelected()
                  })
                ])
              ]
            }
          )
      }
    })
  )

  await fireEvent.click(screen.getByTestId('select-row-0'))
  expect(rowSelection.value).toEqual({ 'row-0': true })

  await dragRow(dragHandles()[0]!)

  expect(rowSelection.value).toEqual({ 'row-0': true })
  expect((screen.getByTestId('select-row-0') as HTMLInputElement).checked).toBe(true)
  expect((screen.getByTestId('select-row-1') as HTMLInputElement).checked).toBe(false)
})
