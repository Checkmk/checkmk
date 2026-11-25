/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterCheckboxList from '@/monitoring/shared/components/filter/FilterCheckboxList.vue'
import type { CheckboxListFilter } from '@/monitoring/shared/components/filter/types'

const definition: CheckboxListFilter<'state'> = {
  type: 'checkbox-list',
  field: 'state',
  options: [
    { value: 'UP', title: 'Up' },
    { value: 'DOWN', title: 'Down' }
  ]
}

test('checks the options a one_of condition already holds', () => {
  const model = ref<ColumnFilterNode<'state'> | undefined>({
    type: 'condition',
    field: 'state',
    op: 'one_of',
    value: ['DOWN']
  })
  render(
    defineComponent({
      components: { FilterCheckboxList },
      setup() {
        return { model, definition }
      },
      template: '<FilterCheckboxList v-model="model" :definition="definition" />'
    })
  )

  expect(screen.getByRole('checkbox', { name: 'Down' })).toBeChecked()
  expect(screen.getByRole('checkbox', { name: 'Up' })).not.toBeChecked()
})
