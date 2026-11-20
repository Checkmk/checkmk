/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterStringInput from '@/monitoring/shared/components/filter/FilterStringInput.vue'
import type { StringInputFilter } from '@/monitoring/shared/components/filter/types'

const definition: StringInputFilter<'name'> = { type: 'string-input', field: 'name' }

test('the free-text field is reachable by name', () => {
  const model = ref<ColumnFilterNode<'name'> | undefined>(undefined)
  render(
    defineComponent({
      components: { FilterStringInput },
      setup() {
        return { model, definition }
      },
      template: '<FilterStringInput v-model="model" :definition="definition" />'
    })
  )

  expect(screen.getByRole('textbox', { name: 'Value' })).toBeInTheDocument()
})

test('an exact match set elsewhere shows in the field, and editing it searches by substring', async () => {
  const contacts: StringInputFilter<'contacts'> = { type: 'string-input', field: 'contacts' }
  const model = ref<ColumnFilterNode<'contacts'> | undefined>({
    type: 'condition',
    field: 'contacts',
    op: 'one_of',
    value: ['foo+bar@example.com']
  })
  render(
    defineComponent({
      components: { FilterStringInput },
      setup() {
        return { model, contacts }
      },
      template: '<FilterStringInput v-model="model" :definition="contacts" />'
    })
  )
  const field = screen.getByRole('textbox', { name: 'Value' })

  expect(field).toHaveValue('foo+bar@example.com')
  expect(screen.getByText('Exact match. Editing searches by substring.')).toBeInTheDocument()

  await userEvent.clear(field)
  await userEvent.type(field, 'adm')

  expect(screen.queryByText('Exact match. Editing searches by substring.')).not.toBeInTheDocument()
  expect(model.value).toStrictEqual({
    type: 'condition',
    field: 'contacts',
    op: 'contains',
    value: 'adm'
  })
})

test('an exact match of several names leaves the field empty', () => {
  const contacts: StringInputFilter<'contacts'> = { type: 'string-input', field: 'contacts' }
  const model = ref<ColumnFilterNode<'contacts'> | undefined>({
    type: 'condition',
    field: 'contacts',
    op: 'one_of',
    value: ['alice', 'bob']
  })
  render(
    defineComponent({
      components: { FilterStringInput },
      setup() {
        return { model, contacts }
      },
      template: '<FilterStringInput v-model="model" :definition="contacts" />'
    })
  )

  expect(screen.getByRole('textbox', { name: 'Value' })).toHaveValue('')
  expect(model.value).toStrictEqual({
    type: 'condition',
    field: 'contacts',
    op: 'one_of',
    value: ['alice', 'bob']
  })
})

test('a regular expression set elsewhere shows in the field as one', () => {
  const model = ref<ColumnFilterNode<'name'> | undefined>({
    type: 'condition',
    field: 'name',
    op: 'matches',
    value: '^web\\-01$'
  })
  render(
    defineComponent({
      components: { FilterStringInput },
      setup() {
        return { model, definition }
      },
      template: '<FilterStringInput v-model="model" :definition="definition" />'
    })
  )

  expect(screen.getByRole('textbox', { name: 'Value' })).toHaveValue('^web\\-01$')
  expect(screen.getByText('Regular expression. Editing searches by substring.')).toBeVisible()
})
