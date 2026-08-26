/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { type ComputedRef, computed, defineComponent, h, nextTick, provide } from 'vue'

import {
  COLUMN_LAYOUT_KEY,
  type ColumnLayoutInfo
} from '@/monitoring/shared/components/MonitoringTableContext'
import StateCell, { type StateCellProps } from '@/monitoring/shared/components/cell/StateCell.vue'

const STATE_COLUMN_ID = 'state'

function mountCell(props: StateCellProps) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(StateCell, props)])])])
      }
    })
  )
}

// The owning MonitoringTable resolves the column widths; this stands in for it
// so the cell can pick the label length its column has room for.
async function mountCellInColumnOfWidth(props: StateCellProps, width: number) {
  const layout: ComputedRef<Map<string, ColumnLayoutInfo>> = computed(
    () =>
      new Map([
        [
          STATE_COLUMN_ID,
          {
            width,
            pinnedLeft: null,
            pinnedRight: null,
            isLastPinned: false,
            isFirstPinnedRight: false,
            justify: 'center' as const
          }
        ]
      ])
  )
  const result = render(
    defineComponent({
      setup() {
        provide(COLUMN_LAYOUT_KEY, layout)
      },
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(StateCell, { columnId: STATE_COLUMN_ID, ...props })])])
        ])
      }
    })
  )
  await nextTick()
  return result
}

test('renders the host state by default', () => {
  mountCell({ state: 'DOWN' })

  expect(screen.getByText('DOWN')).toBeInTheDocument()
})

test('renders the service state when kind is service', () => {
  mountCell({ kind: 'service', state: 'CRIT' })

  expect(screen.getByText('CRITICAL')).toBeInTheDocument()
})

test('forwards the pending flag to the service state', () => {
  mountCell({ kind: 'service', state: 'CRIT', pending: true })

  expect(screen.getByText('PENDING')).toBeInTheDocument()
  expect(screen.queryByText('CRITICAL')).not.toBeInTheDocument()
})

test('renders the stale indicator when stale', () => {
  mountCell({ kind: 'service', state: 'OK', stale: true })

  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})

test('marks the state badge itself as stale', () => {
  const { container } = mountCell({ kind: 'service', state: 'OK', stale: true })

  expect(container.querySelector('.cmk-state-tag--stale')).toHaveTextContent('OK')
})

test('renders the flapping indicator when flapping', () => {
  mountCell({ kind: 'service', state: 'OK', flapping: true })

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
})

test('renders no flapping indicator when not flapping', () => {
  mountCell({ kind: 'service', state: 'OK', flapping: false })

  expect(screen.queryByTitle('Flapping')).not.toBeInTheDocument()
})

test('renders both the flapping and the stale indicator together', () => {
  mountCell({ kind: 'service', state: 'OK', flapping: true, stale: true })

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})

test.each<[StateCellProps, string]>([
  [{ state: 'DOWN' }, 'DO'],
  [{ state: 'UNREACHABLE' }, 'UN'],
  [{ state: 'UP', pending: true }, 'PD'],
  [{ kind: 'service', state: 'CRIT' }, 'CR'],
  [{ kind: 'service', state: 'WARN' }, 'WA']
])('abbreviates the label in a column too narrow to spell it out', async (props, label) => {
  await mountCellInColumnOfWidth(props, 86)

  expect(screen.getByText(label)).toBeInTheDocument()
})

test('spells the label out once the column is wide enough', async () => {
  await mountCellInColumnOfWidth({ state: 'DOWN' }, 131)

  expect(screen.getByText('DOWN')).toBeInTheDocument()
})

test('keeps the stale indicator in a narrow column', async () => {
  await mountCellInColumnOfWidth({ kind: 'service', state: 'OK', stale: true }, 86)

  expect(screen.getByTitle('Stale')).toBeInTheDocument()
  expect(screen.getByText('OK')).toBeInTheDocument()
})

test('keeps the flapping indicator in a narrow column', async () => {
  await mountCellInColumnOfWidth({ kind: 'service', state: 'OK', flapping: true }, 86)

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
  expect(screen.getByText('OK')).toBeInTheDocument()
})
