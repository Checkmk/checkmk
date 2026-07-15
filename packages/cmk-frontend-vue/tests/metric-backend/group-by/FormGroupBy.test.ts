/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import type { GroupByInputType, GroupByModel } from '@/metric-backend/group-by/types'

function renderWidget(initial: Partial<GroupByModel> = {}, inputType: GroupByInputType = 'float') {
  const model = ref<GroupByModel>({ function: 'none', params: {}, keys: [], ...initial })
  const type = ref<GroupByInputType>(inputType)
  const wrapper = defineComponent({
    components: { FormGroupBy },
    setup() {
      return { model, type }
    },
    template: `
      <div>
        <button type="button">outside</button>
        <FormGroupBy v-model="model" :input-type="type" />
      </div>
    `
  })
  render(wrapper)
  return { model, type }
}

async function openPill(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: /Edit group by/ }))
}

async function openFunctionDropdown(): Promise<void> {
  await openPill()
  await userEvent.click(screen.getByRole('combobox', { name: 'Grouping function' }))
}

test('the collapsed chip summarises the clause', () => {
  renderWidget({ function: 'avg', keys: [{ id: '1', level: 'resource', key: 'service.name' }] })
  expect(screen.getByText('avg by [Resource] service.name')).toBeVisible()
})

test.each([
  { fn: 'none' as const, expanded: 'true' },
  { fn: 'avg' as const, expanded: 'false' }
])(
  'entering edit opens the function dropdown only when "no grouping" leaves nothing else to edit',
  async ({ fn, expanded }) => {
    renderWidget({ function: fn, keys: [] }, 'float')
    await openPill()
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Grouping function' })).toHaveAttribute(
        'aria-expanded',
        expanded
      )
    )
  }
)

test.each([
  {
    inputType: 'float' as const,
    initial: { function: 'avg' as const },
    present: ['no grouping', 'avg by', 'count by'],
    absent: ['percentile by']
  },
  {
    inputType: 'histogram' as const,
    initial: { function: 'percentile' as const, params: { quantile: 0.95 } },
    present: ['percentile by', 'fraction below by'],
    absent: ['no grouping']
  }
])(
  'the $inputType input offers its own functions and hides the others',
  async ({ inputType, initial, present, absent }) => {
    renderWidget({ ...initial, keys: [] }, inputType)
    await openFunctionDropdown()

    for (const name of present) {
      expect(await screen.findByRole('option', { name })).toBeVisible()
    }
    for (const name of absent) {
      expect(screen.queryByRole('option', { name })).toBeNull()
    }
  }
)

test('switching the input type resets a now-invalid function to the new default', async () => {
  const { model, type } = renderWidget({ function: 'avg' }, 'float')

  type.value = 'histogram'
  await waitFor(() => expect(model.value.function).toBe('percentile'))
  expect(model.value.params.quantile).toBeDefined()
})

test('the percentile function shows a quantile input, other float functions show none', async () => {
  const { type } = renderWidget({ function: 'percentile', params: { quantile: 0.95 } }, 'histogram')
  await openPill()
  expect(screen.getByLabelText('Quantile (0 to 1)')).toBeVisible()

  type.value = 'float'
  await waitFor(() => expect(screen.queryByLabelText('Quantile (0 to 1)')).toBeNull())
})

test.each([
  {
    scenario: 'an out-of-order fraction pair',
    initial: {
      function: 'fraction_between' as const,
      params: { fractionLowerThreshold: 0.9, fractionUpperThreshold: 0.1 }
    },
    error: 'Lower threshold must be below the upper threshold'
  },
  {
    scenario: 'a missing fraction-below threshold',
    initial: { function: 'fraction_below' as const, params: {} },
    error: 'Enter a threshold'
  }
])('leaving with $scenario is vetoed and reveals the error', async ({ initial, error }) => {
  renderWidget({ ...initial, keys: [] }, 'histogram')
  await openPill()

  await userEvent.click(screen.getByRole('button', { name: 'outside' }))
  expect(screen.getByRole('combobox', { name: 'Grouping function' })).toBeVisible()
  expect(screen.getByText(error)).toBeVisible()
})
