/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h, ref } from 'vue'

import CmkSearchInput from '@/components/CmkSearchInput.vue'

function renderInput(modelValue = '') {
  return render(CmkSearchInput, {
    props: { placeholder: 'Search hosts…', modelValue }
  })
}

test('renders an input with the given placeholder and accessible label', () => {
  renderInput()

  const input = screen.getByRole('searchbox', { name: 'Search hosts…' })
  expect(input).toHaveAttribute('placeholder', 'Search hosts…')
})

test('seeds the input from the model value', () => {
  renderInput('web01')

  expect(screen.getByRole('searchbox', { name: 'Search hosts…' })).toHaveValue('web01')
})

test('hides the clear button while the field is empty', () => {
  renderInput()

  expect(screen.getByRole('button', { name: 'Clear search' })).toHaveClass(
    'cmk-search-input__clear--hidden'
  )
})

test('shows the clear button once the field has content', () => {
  renderInput('web')

  expect(screen.getByRole('button', { name: 'Clear search' })).not.toHaveClass(
    'cmk-search-input__clear--hidden'
  )
})

test('emits the typed query on Enter', async () => {
  const { emitted } = renderInput()

  await fireEvent.update(screen.getByRole('searchbox'), 'db')
  await fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })

  expect(emitted('search')).toEqual([['db']])
})

test('keeps the model value in sync while typing', async () => {
  const { emitted } = renderInput()

  await fireEvent.update(screen.getByRole('searchbox'), 'db')

  expect(emitted('update:modelValue')).toEqual([['db']])
})

test('clears the field and emits an empty query when the clear button is clicked', async () => {
  const { emitted } = renderInput('web01')

  await fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))

  expect(screen.getByRole('searchbox')).toHaveValue('')
  expect(emitted('search')).toEqual([['']])
})

test('emits an empty query on clear even when the model is parent-controlled', async () => {
  const model = ref('web01')
  const searched: string[] = []

  const testComponent = defineComponent({
    setup() {
      return () =>
        h(CmkSearchInput, {
          placeholder: 'Search hosts…',
          modelValue: model.value,
          'onUpdate:modelValue': (v: string) => {
            model.value = v
          },
          onSearch: (q: string) => {
            searched.push(q)
          }
        })
    }
  })

  render(testComponent)

  await fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))

  expect(screen.getByRole('searchbox')).toHaveValue('')
  expect(model.value).toBe('')
  expect(searched).toEqual([''])
})
