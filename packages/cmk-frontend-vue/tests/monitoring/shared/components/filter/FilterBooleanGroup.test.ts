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

  expect(screen.getByRole('group', { name: 'In downtime' })).toBeInTheDocument()
  expect(screen.getByRole('group', { name: 'Acknowledged' })).toBeInTheDocument()
})

test('the repeated "Any" option is told apart by its group', () => {
  renderFilter()

  const downtime = screen.getByRole('group', { name: 'In downtime' })
  const acknowledged = screen.getByRole('group', { name: 'Acknowledged' })

  expect(within(downtime).getByRole('button', { name: 'Toggle Any' })).not.toBe(
    within(acknowledged).getByRole('button', { name: 'Toggle Any' })
  )
})

test('the icon buttons carry the same three words the legend heads them with', () => {
  renderFilter()

  const group = screen.getByRole('group', { name: 'Acknowledged' })
  const buttonLabels = within(group)
    .getAllByRole('button')
    .map((button) => button.getAttribute('aria-label'))
  const legendLabels = ['Any', 'Yes', 'No'].map((word) => screen.getByText(word).textContent)

  expect(buttonLabels).toEqual(legendLabels.map((word) => `Toggle ${word}`))
})
