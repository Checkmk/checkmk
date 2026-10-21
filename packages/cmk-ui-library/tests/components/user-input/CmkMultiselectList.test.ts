/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkMultiselectList from 'cmk-ui-library/components/user-input/CmkMultiselectList.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { defineComponent, h, ref } from 'vue'

function items(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    name: `item${i}`,
    title: untranslated(`Item ${i}`)
  }))
}

function renderList(count: number, initial: string[] = []) {
  const selected = ref<string[]>(initial)
  render(
    defineComponent({
      setup: () => () =>
        h(CmkMultiselectList, {
          modelValue: selected.value,
          'onUpdate:modelValue': (value: string[]) => (selected.value = value),
          items: items(count),
          label: untranslated('Columns'),
          emptyText: untranslated('No matching columns')
        })
    })
  )
  return selected
}

test('selecting an item keeps the selection in the order of the items', async () => {
  const user = userEvent.setup()
  const selected = renderList(3, ['item2'])

  await user.click(screen.getByRole('checkbox', { name: 'Item 0' }))

  expect(selected.value).toEqual(['item0', 'item2'])
})

test('deselecting an item drops it from the selection', async () => {
  const user = userEvent.setup()
  const selected = renderList(3, ['item0', 'item1'])

  await user.click(screen.getByRole('checkbox', { name: 'Item 0' }))

  expect(selected.value).toEqual(['item1'])
})

test('a short list offers no search', () => {
  renderList(8)

  expect(screen.queryByRole('searchbox')).not.toBeInTheDocument()
})

test('the search narrows the list down to the matching items', async () => {
  const user = userEvent.setup()
  renderList(12)

  await user.type(screen.getByRole('searchbox'), 'item 1')

  expect(screen.getAllByRole('checkbox').map((box) => box.closest('li')?.textContent)).toEqual([
    'Item 1',
    'Item 10',
    'Item 11'
  ])
})

test('a search without a match shows the empty text', async () => {
  const user = userEvent.setup()
  renderList(12)

  await user.type(screen.getByRole('searchbox'), 'nothing')

  expect(screen.getByText('No matching columns')).toBeInTheDocument()
})
