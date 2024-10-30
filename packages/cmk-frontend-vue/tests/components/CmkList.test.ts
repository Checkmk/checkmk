/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { defineComponent } from 'vue'
import { screen, render, fireEvent } from '@testing-library/vue'
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
                :draggable="{ onReorder: () => {} }"
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
