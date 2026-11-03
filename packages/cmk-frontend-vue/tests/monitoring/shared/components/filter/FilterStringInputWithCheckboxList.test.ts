/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterStringInputWithCheckboxList from '@/monitoring/shared/components/filter/FilterStringInputWithCheckboxList.vue'
import type { StringInputWithCheckboxListFilter } from '@/monitoring/shared/components/filter/types'

type Field = 'host_name' | 'host_state'

const definition: StringInputWithCheckboxListFilter<'host_name', 'host_state'> = {
  type: 'string-input-with-checkbox-list',
  field: 'host_name',
  checkboxField: 'host_state',
  options: [
    { value: 'DOWN', title: 'Down' },
    { value: 'UP', title: 'Up' }
  ]
}

const SEARCH: ColumnFilterNode<Field> = {
  type: 'condition',
  field: 'host_name',
  op: 'contains',
  value: 'web'
}

const DOWN: ColumnFilterNode<Field> = {
  type: 'condition',
  field: 'host_state',
  op: 'one_of',
  value: ['DOWN']
}

function renderFilter(initial?: ColumnFilterNode<Field>) {
  const model = ref<ColumnFilterNode<Field> | undefined>(initial)
  render(
    defineComponent({
      components: { FilterStringInputWithCheckboxList },
      setup() {
        return { model, definition }
      },
      template: '<FilterStringInputWithCheckboxList v-model="model" :definition="definition" />'
    })
  )
  return { model }
}

test('a typed search alone filters on the text field', async () => {
  const user = userEvent.setup()
  const { model } = renderFilter()

  await user.type(screen.getByRole('textbox', { name: 'Value' }), 'web')

  expect(model.value).toEqual(SEARCH)
})

test('a checked option alone filters on the checkbox field', async () => {
  const user = userEvent.setup()
  const { model } = renderFilter()

  await user.click(screen.getByRole('checkbox', { name: 'Down' }))

  expect(model.value).toEqual(DOWN)
})

test('a search and a checked option must both match', async () => {
  const user = userEvent.setup()
  const { model } = renderFilter(SEARCH)

  await user.click(screen.getByRole('checkbox', { name: 'Down' }))

  expect(model.value).toEqual({ type: 'and', children: [SEARCH, DOWN] })
})

test('clearing the search keeps the checked options', async () => {
  const user = userEvent.setup()
  const { model } = renderFilter({ type: 'and', children: [SEARCH, DOWN] })

  await user.clear(screen.getByRole('textbox', { name: 'Value' }))

  expect(model.value).toEqual(DOWN)
})

test('both halves show what the filter already holds', () => {
  renderFilter({ type: 'and', children: [SEARCH, DOWN] })

  expect(screen.getByRole('textbox', { name: 'Value' })).toHaveValue('web')
  expect(screen.getByRole('checkbox', { name: 'Down' })).toBeChecked()
  expect(screen.getByRole('checkbox', { name: 'Up' })).not.toBeChecked()
})
