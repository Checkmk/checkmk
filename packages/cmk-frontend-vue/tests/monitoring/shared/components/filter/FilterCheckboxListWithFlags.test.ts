/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterCheckboxListWithFlags from '@/monitoring/shared/components/filter/FilterCheckboxListWithFlags.vue'
import type { CheckboxListWithFlagsFilter } from '@/monitoring/shared/components/filter/types'

type Field = 'state' | 'stale' | 'acknowledged'

const definition: CheckboxListWithFlagsFilter<'state', 'stale' | 'acknowledged'> = {
  type: 'checkbox-list-with-flags',
  field: 'state',
  options: [
    { value: 'UP', title: 'Up' },
    { value: 'DOWN', title: 'Down' }
  ],
  flags: [
    { field: 'stale', title: 'Stale' },
    { field: 'acknowledged', title: 'Acknowledged' }
  ]
}

test('the states and the flags show what the filter already holds', () => {
  const model = ref<ColumnFilterNode<Field> | undefined>({
    type: 'and',
    children: [
      { type: 'condition', field: 'state', op: 'one_of', value: ['DOWN'] },
      { type: 'condition', field: 'stale', op: 'eq', value: true }
    ]
  })
  render(
    defineComponent({
      components: { FilterCheckboxListWithFlags },
      setup() {
        return { model, definition }
      },
      template: '<FilterCheckboxListWithFlags v-model="model" :definition="definition" />'
    })
  )

  expect(screen.getByRole('checkbox', { name: 'Down' })).toBeChecked()
  expect(screen.getByRole('checkbox', { name: 'Up' })).not.toBeChecked()
  expect(
    within(screen.getByRole('group', { name: 'Stale' })).getByRole('button', { name: 'Toggle Yes' })
  ).toHaveAttribute('aria-pressed', 'true')
  expect(
    within(screen.getByRole('group', { name: 'Acknowledged' })).getByRole('button', {
      name: 'Toggle Any'
    })
  ).toHaveAttribute('aria-pressed', 'true')
})
