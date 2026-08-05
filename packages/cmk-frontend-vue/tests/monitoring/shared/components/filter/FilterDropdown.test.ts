/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, h, nextTick, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'
import FilterDropdown from '@/monitoring/shared/components/filter/FilterDropdown.vue'
import type {
  CheckboxListFilter,
  ColumnFilterValue
} from '@/monitoring/shared/components/filter/types'

const definition: CheckboxListFilter<'state'> = {
  type: 'checkbox-list',
  field: 'state',
  options: [
    { value: 'UP', title: 'UP' },
    { value: 'DOWN', title: 'DOWN' }
  ]
}

function upFilter(): ColumnFilterNode<'state'> {
  return { type: 'condition', field: 'state', op: 'one_of', value: ['UP'] }
}

// Wrapper holding the committed model so we can observe what the dropdown
// commits, and supplying the trigger slot the shell expects.
function renderDropdown(initial: ColumnFilterNode<FilterField> | undefined = undefined) {
  const model = ref<ColumnFilterNode<FilterField> | undefined>(initial)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(
          FilterDropdown,
          {
            definition: definition,
            label: 'State',
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

test('toggling an option does not commit to the model before Apply', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))

  expect(model.value).toBeUndefined()
})

test('Apply commits the staged selection and closes the dropdown', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toEqual(upFilter())
  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument()
})

test('Close discards the staged selection and leaves the model untouched', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(model.value).toBeUndefined()
  expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
})

test('a closed edit is gone when the dropdown is reopened', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown(upFilter())

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'DOWN' }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.getByRole('checkbox', { name: 'UP' })).toBeChecked()
  expect(screen.getByRole('checkbox', { name: 'DOWN' })).not.toBeChecked()
  expect(model.value).toEqual(upFilter())
})

test('a click that unmounts its own target does not close the funnel', async () => {
  const user = userEvent.setup()
  renderDropdown()
  await user.click(screen.getByRole('button', { name: 'Open' }))
  const panel = screen.getByRole('group', { name: 'Filter State' })

  // Stands in for floating content that unmounts as it is activated - a dropdown
  // option, say. It is still in the panel at pointerdown and detached by the time
  // the document-level click handler runs, so a containment check made then sees
  // a node that is inside nothing at all.
  const option = document.createElement('button')
  option.addEventListener('click', () => option.remove())
  panel.appendChild(option)

  option.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
  option.dispatchEvent(new MouseEvent('click', { bubbles: true }))
  await nextTick()

  expect(screen.queryByRole('group', { name: 'Filter State' })).not.toBeNull()
})
