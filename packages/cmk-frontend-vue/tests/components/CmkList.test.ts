/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import CmkList from '@/components/CmkList/CmkList.vue'

test('CmkList does not submit form when clicking drag button', async () => {
  const submitHandler = vi.fn((e) => e.preventDefault())
  try {
    document.addEventListener('submit', submitHandler)

    const testComponent = defineComponent({
      components: { CmkList },
      template: `
          <form>
            <CmkList
                :items-props="{ itemData: ['foo'] }"
                :dragCallbacks="{ onReorder: () => {} }"
                :try-delete="() => {}"
            >
                <template #item="{ itemData }">
                    <span>itemData</span>
                </template>
            </CmkList>
          </form>
        `
    })

    render(testComponent)

    const draggable = screen.getByRole('button', { name: 'Drag to reorder' })
    await fireEvent.click(draggable)

    expect(submitHandler).not.toHaveBeenCalled()
  } finally {
    document.removeEventListener('submit', submitHandler)
  }
})

test('CmkList reorders items when dragging and dropping', async () => {
  const onReorder = vi.fn()

  const testComponent = defineComponent({
    components: { CmkList },
    setup() {
      return { onReorder }
    },
    template: `
      <CmkList
          :items-props="{ itemData: ['Item 1', 'Item 2', 'Item 3'] }"
          :dragCallbacks="{ onReorder }"
          :try-delete="() => true"
      >
          <template #item-props="{ itemData }">
              <span>{{ itemData }}</span>
          </template>
      </CmkList>
    `
  })

  render(testComponent)

  expect(screen.getByText('Item 1')).toBeInTheDocument()
  expect(screen.getByText('Item 2')).toBeInTheDocument()
  expect(screen.getByText('Item 3')).toBeInTheDocument()

  const dragButtons = screen.getAllByRole('button', { name: 'Drag to reorder' })
  expect(dragButtons).toHaveLength(3)

  const listItems = screen.getAllByRole('listitem')
  expect(listItems).toHaveLength(3)

  const mockRect = (top: number, height: number) => ({
    top,
    height,
    bottom: top + height,
    left: 0,
    right: 100,
    width: 100,
    x: 0,
    y: top,
    toJSON: () => ({})
  })

  // Set up mock positions: each row is 50px tall, starting at y=0
  const rows = listItems.map((item) => item.closest('tr')!)
  rows[0]!.getBoundingClientRect = vi.fn(() => mockRect(0, 50))
  rows[1]!.getBoundingClientRect = vi.fn(() => mockRect(50, 50))
  rows[2]!.getBoundingClientRect = vi.fn(() => mockRect(100, 50))

  // Drag the first item (index 0) to the third position (index 2)
  const firstDragButton = dragButtons[0]!
  await fireEvent.dragStart(firstDragButton, { clientY: 25 })

  // Create a dragover event to update the mouse position (simulates moving down past the midpoint of the third item)
  // Row 2 has midpoint at 125, so we need to go past that to move to position 2
  const dragOverEvent = new MouseEvent('dragover', { clientY: 130, bubbles: true })
  window.dispatchEvent(dragOverEvent)

  // Simulate dragging over the third item (past its midpoint)
  await fireEvent.drag(firstDragButton, { clientY: 130 })

  // End the drag
  await fireEvent.dragEnd(firstDragButton, { clientY: 130 })

  // Verify onReorder was called with the new order: [1, 2, 0]
  // (item at index 0 moved to position 2)
  expect(onReorder).toHaveBeenCalledWith([1, 2, 0])
})
