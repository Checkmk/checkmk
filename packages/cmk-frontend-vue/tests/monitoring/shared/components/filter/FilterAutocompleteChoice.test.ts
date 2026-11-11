/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterAutocompleteChoice from '@/monitoring/shared/components/filter/FilterAutocompleteChoice.vue'
import type { AutocompleteChoiceFilter } from '@/monitoring/shared/components/filter/types'

const LABELS = ['cmk/os_family:linux', 'criticality:prod']

function mountFunnel(op: 'one_of' | 'all_of') {
  const model = ref<ColumnFilterNode<'labels'> | undefined>(undefined)
  const definition: AutocompleteChoiceFilter<'labels'> = {
    type: 'autocomplete-choice',
    field: 'labels',
    op,
    keyValue: true,
    suggest: (query: string) => Promise.resolve(LABELS.filter((label) => label.includes(query)))
  }
  render(
    defineComponent({
      components: { FilterAutocompleteChoice },
      setup() {
        return { model, definition }
      },
      template: '<FilterAutocompleteChoice v-model="model" :definition="definition" />'
    })
  )
  return model
}

async function pick(label: string): Promise<void> {
  await userEvent.type(screen.getByRole('searchbox'), label)
  await waitFor(() => screen.getByRole('button', { name: label }))
  await userEvent.click(screen.getByRole('button', { name: label }))
}

test.each(['all_of', 'one_of'] as const)('commits every pick as one %s condition', async (op) => {
  const model = mountFunnel(op)

  for (const label of LABELS) {
    await pick(label)
  }

  expect(model.value).toEqual({
    type: 'condition',
    field: 'labels',
    op,
    value: LABELS
  })
})

test('the AND/OR switch starts at the default the definition gives', () => {
  mountFunnel('one_of')

  const combine = screen.getByRole('group', { name: 'Combine selections with' })
  expect(within(combine).getByRole('button', { name: 'Toggle OR' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
})

test('switching to OR turns the picks into a one_of condition', async () => {
  const model = mountFunnel('all_of')

  for (const label of LABELS) {
    await pick(label)
  }
  const combine = screen.getByRole('group', { name: 'Combine selections with' })
  await userEvent.click(within(combine).getByRole('button', { name: 'Toggle OR' }))

  expect(model.value).toEqual({ type: 'condition', field: 'labels', op: 'one_of', value: LABELS })
})

test('a switch flipped before the first pick applies to it', async () => {
  const model = mountFunnel('one_of')

  const combine = screen.getByRole('group', { name: 'Combine selections with' })
  await userEvent.click(within(combine).getByRole('button', { name: 'Toggle AND' }))
  await pick(LABELS[0]!)

  expect(model.value).toEqual({
    type: 'condition',
    field: 'labels',
    op: 'all_of',
    value: [LABELS[0]]
  })
})
