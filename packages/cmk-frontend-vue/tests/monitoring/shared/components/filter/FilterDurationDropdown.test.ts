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
import type { ColumnFilterValue, DurationFilter } from '@/monitoring/shared/components/filter/types'

const definition: DurationFilter<'last_state_change'> = {
  type: 'duration',
  field: 'last_state_change'
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
            label: 'Last state change',
            modelValue: model.value,
            'onUpdate:modelValue': (value: ColumnFilterValue<FilterField> | undefined) => {
              model.value = value as ColumnFilterNode<FilterField> | undefined
            }
          },
          {
            trigger: ({ toggle }: { toggle: () => void }) =>
              h('button', { type: 'button', onClick: toggle }, 'Open')
          }
        )
    }
  })
  return { model, ...render(wrapper) }
}

test('applying an age commits the relative bound', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '5')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toEqual({
    type: 'age',
    field: 'last_state_change',
    op: 'younger_than',
    seconds: 5 * 60
  })
})

test('an inverted span is not committed', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('button', { name: 'Toggle Between' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Younger bound' }), '30')
  await user.type(screen.getByRole('spinbutton', { name: 'Older bound' }), '5')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toBeUndefined()
})

test('a refused span keeps the popover open on the message it reveals', async () => {
  const user = userEvent.setup()
  renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('button', { name: 'Toggle Between' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Younger bound' }), '30')
  await user.type(screen.getByRole('spinbutton', { name: 'Older bound' }), '5')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(
    await screen.findByText('Enter a younger bound that does not exceed the older one.')
  ).toBeInTheDocument()
  expect(screen.getByRole('spinbutton', { name: 'Younger bound' })).toBeInTheDocument()
})

test('an age in the future is not committed', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '-5')
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toBeUndefined()
})
