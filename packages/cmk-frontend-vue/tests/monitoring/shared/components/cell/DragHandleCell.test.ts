/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h, provide } from 'vue'

import {
  ROW_DRAG_KEY,
  type RowDragHandlers
} from '@/monitoring/shared/components/MonitoringTableContext'
import DragHandleCell from '@/monitoring/shared/components/cell/DragHandleCell.vue'

function mountCell(dragHandlers?: RowDragHandlers) {
  return render(
    defineComponent({
      setup() {
        if (dragHandlers) {
          provide(ROW_DRAG_KEY, dragHandlers)
        }
      },
      render() {
        return h('table', [h('tbody', [h('tr', [h(DragHandleCell)])])])
      }
    })
  )
}

function makeHandlers(): RowDragHandlers {
  return { dragStart: vi.fn(), drag: vi.fn(), dragEnd: vi.fn() }
}

test('renders no handle without a providing table', () => {
  mountCell()

  expect(screen.queryByRole('button', { name: 'Drag to reorder' })).not.toBeInTheDocument()
})

test('renders a draggable handle and forwards the drag events', async () => {
  const handlers = makeHandlers()
  mountCell(handlers)

  const handle = screen.getByRole('button', { name: 'Drag to reorder' })
  expect(handle).toHaveAttribute('draggable', 'true')
  expect(handle.tagName).toBe('BUTTON')

  handle.focus()
  expect(handle).toHaveFocus()

  await fireEvent(handle, new MouseEvent('dragstart', { bubbles: true }))
  await fireEvent(handle, new MouseEvent('drag', { bubbles: true }))
  await fireEvent(handle, new MouseEvent('dragend', { bubbles: true }))

  expect(handlers.dragStart).toHaveBeenCalledTimes(1)
  expect(handlers.drag).toHaveBeenCalledTimes(1)
  expect(handlers.dragEnd).toHaveBeenCalledTimes(1)
})
