/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterBooleanGroup from '@/monitoring/shared/components/filter/FilterBooleanGroup.vue'
import type { BooleanGroupFilter } from '@/monitoring/shared/components/filter/types'

type ModeField = 'in_downtime' | 'acknowledged'

const definition: BooleanGroupFilter<ModeField> = {
  type: 'boolean-group',
  groups: [
    { field: 'in_downtime', title: 'In downtime' },
    { field: 'acknowledged', title: 'Acknowledged' }
  ]
}

function renderFilter() {
  const model = ref<ColumnFilterNode<ModeField> | undefined>(undefined)
  render(
    defineComponent({
      components: { FilterBooleanGroup },
      setup() {
        return { model, definition }
      },
      template: '<FilterBooleanGroup v-model="model" :definition="definition" />'
    })
  )
  return { model }
}

test('each group carries the name of the field it switches', () => {
  renderFilter()

  expect(screen.getByRole('radiogroup', { name: 'In downtime' })).toBeInTheDocument()
  expect(screen.getByRole('radiogroup', { name: 'Acknowledged' })).toBeInTheDocument()
})

test('the repeated "All" option is told apart by its group', () => {
  renderFilter()

  const downtime = screen.getByRole('radiogroup', { name: 'In downtime' })
  const acknowledged = screen.getByRole('radiogroup', { name: 'Acknowledged' })

  expect(within(downtime).getByRole('radio', { name: 'All' })).not.toBe(
    within(acknowledged).getByRole('radio', { name: 'All' })
  )
})
