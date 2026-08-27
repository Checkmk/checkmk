/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render } from '@testing-library/vue'
import { type ComputedRef, computed, defineComponent, h, nextTick, provide } from 'vue'

import {
  COLUMN_LAYOUT_KEY,
  type CellBreakpoints,
  type ColumnLayoutInfo
} from '@/monitoring/shared/components/MonitoringTableContext'
import BaseCell, { type CellVerticalAlign } from '@/monitoring/shared/components/cell/BaseCell.vue'

type CellProps = {
  breakpoints?: CellBreakpoints
  button?: boolean
  onClick?: (payload: MouseEvent) => void
  verticalAlign?: CellVerticalAlign
  noWrap?: boolean
}

const TEST_COLUMN_ID = 'col'

// BaseCell no longer measures itself; the owning MonitoringTable provides the
// resolved per-column layout keyed by column id. The test stands in for that
// table by providing a single-column layout whose width drives the breakpoint
// selection, and addresses it via the cell's `columnId` prop.
async function mountCell(
  props: CellProps = {},
  options: { cellWidth?: number; slots?: Record<string, () => unknown> } = {}
) {
  const slots = options.slots ?? { default: () => 'cell content' }
  const layout: ComputedRef<Map<string, ColumnLayoutInfo>> = computed(
    () =>
      new Map([
        [
          TEST_COLUMN_ID,
          {
            width: options.cellWidth ?? null,
            pinnedLeft: null,
            pinnedRight: null,
            isLastPinned: false,
            isFirstPinnedRight: false,
            justify: 'left' as const
          }
        ]
      ])
  )
  const result = render(
    defineComponent({
      components: { BaseCell },
      setup() {
        provide(COLUMN_LAYOUT_KEY, layout)
      },
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(BaseCell, { columnId: TEST_COLUMN_ID, ...props }, slots)])])
        ])
      }
    })
  )
  // Let the width propagate to activeSlot.
  await nextTick()
  return result
}

test('renders a <td> with default slot content', async () => {
  const { container } = await mountCell({}, { cellWidth: 500 })
  const td = container.querySelector('td')
  expect(td).not.toBeNull()
  expect(td).toHaveTextContent('cell content')
})

test('renders the largest-fitting named slot from breakpoints', async () => {
  const { container } = await mountCell(
    { breakpoints: { short: 's', long: 'l', verbose: 'xl' } },
    {
      cellWidth: 900,
      slots: {
        short: () => 'short',
        long: () => 'long',
        verbose: () => 'verbose'
      }
    }
  )
  expect(container.querySelector('td')).toHaveTextContent('long')
})

test('falls back to the default slot when no breakpoint slot matches the current width', async () => {
  const { container } = await mountCell(
    { breakpoints: { long: 'l', verbose: 'xl' } },
    {
      cellWidth: 200,
      slots: {
        default: () => 'fallback',
        long: () => 'long',
        verbose: () => 'verbose'
      }
    }
  )
  expect(container.querySelector('td')).toHaveTextContent('fallback')
})

test('renders a native <button> and emits click when the button prop is set', async () => {
  const onClick = vi.fn()
  const { container } = await mountCell({ button: true, onClick }, { cellWidth: 500 })
  const button = container.querySelector('button')
  expect(button).not.toBeNull()
  await userEvent.click(button!)
  expect(onClick).toHaveBeenCalledTimes(1)
})

test('renders no button and emits nothing without the button prop', async () => {
  const { container } = await mountCell({}, { cellWidth: 500 })
  expect(container.querySelector('button')).toBeNull()
})

test('offers the open-details icon inside the button', async () => {
  const { container } = await mountCell({ button: true }, { cellWidth: 500 })
  expect(container.querySelector('button .monitoring-base-cell__action-icon')).not.toBeNull()
})

test('marks the cell so the button can cover it entirely', async () => {
  const { container } = await mountCell({ button: true }, { cellWidth: 500 })
  expect(container.querySelector('td')).toHaveClass('monitoring-base-cell--button')
})

test('offers no open-details icon without the button prop', async () => {
  const { container } = await mountCell({}, { cellWidth: 500 })
  expect(container.querySelector('.monitoring-base-cell__action-icon')).toBeNull()
})

test('is top-aligned and wrapping by default', async () => {
  const { container } = await mountCell({}, { cellWidth: 500 })
  const td = container.querySelector('td')
  expect(td).not.toHaveClass('monitoring-base-cell--vertical-middle')
  expect(td).not.toHaveClass('monitoring-base-cell--no-wrap')
})

test('centers the content vertically with verticalAlign middle', async () => {
  const { container } = await mountCell({ verticalAlign: 'middle' }, { cellWidth: 500 })
  expect(container.querySelector('td')).toHaveClass('monitoring-base-cell--vertical-middle')
})

test('suppresses line wrapping with noWrap', async () => {
  const { container } = await mountCell({ noWrap: true }, { cellWidth: 500 })
  expect(container.querySelector('td')).toHaveClass('monitoring-base-cell--no-wrap')
})

test('skips named slots that the consumer did not provide', async () => {
  const { container } = await mountCell(
    { breakpoints: { short: 's', long: 'l' } },
    {
      cellWidth: 1000,
      slots: {
        short: () => 'short',
        default: () => 'default'
        // `long` slot intentionally not provided
      }
    }
  )
  expect(container.querySelector('td')).toHaveTextContent('short')
})
