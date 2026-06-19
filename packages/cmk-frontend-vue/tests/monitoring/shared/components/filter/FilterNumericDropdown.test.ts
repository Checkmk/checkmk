/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, h, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'
import FilterDropdown from '@/monitoring/shared/components/filter/FilterDropdown.vue'
import type { NumericFilter } from '@/monitoring/shared/components/filter/types'

const definition: NumericFilter<'num_services'> = {
  type: 'numeric',
  field: 'num_services',
  unit: 'services'
}

function renderDropdown(initial: ColumnFilterNode<FilterField> | undefined = undefined) {
  const model = ref<ColumnFilterNode<FilterField> | undefined>(initial)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(
          FilterDropdown,
          {
            definition,
            label: 'Services',
            modelValue: model.value,
            'onUpdate:modelValue': (value: ColumnFilterNode<FilterField> | undefined) => {
              model.value = value
            }
          },
          {
            trigger: ({ toggle, isActive }: { toggle: () => void; isActive: boolean }) =>
              h(
                'button',
                { type: 'button', onClick: toggle, 'data-active': String(isActive) },
                'Open'
              )
          }
        )
    }
  })
  return { model, ...render(wrapper) }
}

test('applying a numeric range commits the condition node', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('spinbutton', { name: 'From' }), '3')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toEqual({ type: 'condition', field: 'num_services', op: 'gte', value: 3 })
})

test('a previously applied value is shown again on reopen', async () => {
  const user = userEvent.setup()
  renderDropdown({ type: 'condition', field: 'num_services', op: 'gte', value: 3 })

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(3)
})

test('a range entered from scratch survives apply and reopen', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('spinbutton', { name: 'From' }), '3')
  await user.type(screen.getByRole('spinbutton', { name: 'To' }), '10')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 3 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 10 }
    ]
  })
  expect(screen.getByRole('button', { name: 'Open' })).toHaveAttribute('data-active', 'true')

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(3)
  expect(screen.getByRole('spinbutton', { name: 'To' })).toHaveValue(10)
})

test('a second edit refines the already-applied value', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 3
  })

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('spinbutton', { name: 'To' }), '10')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 3 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 10 }
    ]
  })
})
