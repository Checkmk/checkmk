/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render } from '@testing-library/vue'
import { onTestFinished } from 'vitest'
import { type ComputedRef, computed, defineComponent, h, nextTick, provide } from 'vue'

import {
  COLUMN_LAYOUT_KEY,
  type CellBreakpoints,
  type ColumnLayoutInfo
} from '@/monitoring/shared/components/MonitoringTableContext'
import BaseCell, { type CellVerticalAlign } from '@/monitoring/shared/components/cell/BaseCell.vue'

import { markText, pastDoubleClick, userOnFakeClock } from '../../deferredClick'

type CellProps = {
  breakpoints?: CellBreakpoints
  button?: boolean
  interactive?: boolean
  instant?: boolean
  buttonLabel?: string
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

test('exposes its column id on the <td>', async () => {
  const { container } = await mountCell({}, { cellWidth: 500 })
  expect(container.querySelector('td')).toHaveAttribute('data-column-id', TEST_COLUMN_ID)
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

test('marks the cell as clickable as a whole', async () => {
  const { container } = await mountCell({ button: true }, { cellWidth: 500 })
  expect(container.querySelector('td')).toHaveClass('monitoring-base-cell--button')
})

test('emits click for a click on its content, which stays out of the button', async () => {
  const onClick = vi.fn()
  const { getByText } = await mountCell({ button: true, onClick }, { cellWidth: 500 })

  const user = userOnFakeClock()

  expect(getByText('cell content').closest('button')).toBeNull()
  await user.click(getByText('cell content'))
  expect(onClick).not.toHaveBeenCalled()
  await pastDoubleClick()

  expect(onClick).toHaveBeenCalledOnce()
})

test('emits an instant click at once', async () => {
  const onClick = vi.fn()
  const { getByText } = await mountCell(
    { button: true, instant: true, onClick },
    { cellWidth: 500 }
  )
  const user = userOnFakeClock()

  await user.click(getByText('cell content'))

  expect(onClick).toHaveBeenCalledOnce()
})

test('emits click at once for Enter on the open-details button', async () => {
  const onClick = vi.fn()
  const { getByRole } = await mountCell({ button: true, onClick }, { cellWidth: 500 })
  const user = userOnFakeClock()

  getByRole('button').focus()
  await user.keyboard('{Enter}')

  expect(onClick).toHaveBeenCalledOnce()
})

test('emits no click for a double-click marking its text', async () => {
  const onClick = vi.fn()
  const { getByText } = await mountCell({ button: true, onClick }, { cellWidth: 500 })

  const user = userOnFakeClock()

  await user.dblClick(getByText('cell content'))
  await pastDoubleClick()

  expect(onClick).not.toHaveBeenCalled()
})

test('emits no click when a press elsewhere follows the click', async () => {
  const onClick = vi.fn()
  const { getByText } = await mountCell({ button: true, onClick }, { cellWidth: 500 })
  const user = userOnFakeClock()

  await user.click(getByText('cell content'))
  await user.pointer({ keys: '[MouseLeft]', target: document.body })
  await pastDoubleClick()

  expect(onClick).not.toHaveBeenCalled()
})

test('emits no click for a click with a modifier key', async () => {
  const onClick = vi.fn()
  const { getByText } = await mountCell({ button: true, onClick }, { cellWidth: 500 })

  const user = userOnFakeClock()
  await user.keyboard('{Control>}')
  await user.click(getByText('cell content'))
  await user.keyboard('{/Control}')
  await pastDoubleClick()

  expect(onClick).not.toHaveBeenCalled()
})

test('lets a click in an interactive cell reach the document, which closes open popups', async () => {
  const onDocumentClick = vi.fn()
  const { getByText } = await mountCell({ interactive: true }, { cellWidth: 500 })
  document.body.addEventListener('click', onDocumentClick)
  onTestFinished(() => document.body.removeEventListener('click', onDocumentClick))

  await userEvent.click(getByText('cell content'))

  expect(onDocumentClick).toHaveBeenCalledOnce()
})

test('emits no click when the click ends marking its text', async () => {
  const onClick = vi.fn()
  const { getByText } = await mountCell({ button: true, onClick }, { cellWidth: 500 })
  const user = userOnFakeClock()

  await markText(user, getByText('cell content'))
  await pastDoubleClick()

  expect(onClick).not.toHaveBeenCalled()
})

test('lets a click in a button cell reach the document, which closes open popups', async () => {
  const onDocumentClick = vi.fn()
  const { getByText } = await mountCell({ button: true }, { cellWidth: 500 })
  document.body.addEventListener('click', onDocumentClick)
  onTestFinished(() => document.body.removeEventListener('click', onDocumentClick))

  await userEvent.click(getByText('cell content'))

  expect(onDocumentClick).toHaveBeenCalledOnce()
})

test('emits one click for a click on the open-details button', async () => {
  const onClick = vi.fn()
  const { getByRole } = await mountCell({ button: true, onClick }, { cellWidth: 500 })
  const user = userOnFakeClock()

  await user.click(getByRole('button'))
  await pastDoubleClick()

  expect(onClick).toHaveBeenCalledOnce()
})

test('names the open-details button after its label', async () => {
  const { getByRole } = await mountCell(
    { button: true, buttonLabel: 'CPU load' },
    { cellWidth: 500 }
  )

  expect(getByRole('button', { name: 'CPU load' })).toBeInTheDocument()
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
