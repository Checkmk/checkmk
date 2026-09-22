/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
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
