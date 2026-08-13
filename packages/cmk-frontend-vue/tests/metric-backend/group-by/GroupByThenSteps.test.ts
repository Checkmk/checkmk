/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import GroupByThenSteps from '@/metric-backend/group-by/GroupByThenSteps.vue'
import type { AggregationStep, GroupKey } from '@/metric-backend/group-by/types'

const GROUP_BY_KEYS: GroupKey[] = [
  { id: 'a', attributeKind: 'resource', attributeKey: 'service.name' },
  { id: 'b', attributeKind: 'data_point', attributeKey: 'http.route' }
]

function renderSteps(initial: AggregationStep[] = [], groupByKeys: GroupKey[] = GROUP_BY_KEYS) {
  const thenSteps = ref<AggregationStep[]>(initial)
  const wrapper = defineComponent({
    components: { GroupByThenSteps },
    setup() {
      return { thenSteps, groupByKeys }
    },
    // GroupByThenSteps emits <tr> rows, so host it in a table.
    template: `
      <table>
        <tbody>
          <GroupByThenSteps v-model="thenSteps" :group-by-keys="groupByKeys" />
        </tbody>
      </table>
    `
  })
  render(wrapper)
  return { thenSteps }
}

test('the add button appends an "avg by everything" step, opened for editing', async () => {
  const { thenSteps } = renderSteps()
  await userEvent.click(screen.getByRole('button', { name: 'Add then step' }))
  await waitFor(() => expect(thenSteps.value).toHaveLength(1))
  expect(thenSteps.value[0]).toMatchObject({ function: 'avg', keys: [] })
  // The new step lands open with its function picker already dropped down, not a collapsed chip.
  const fnDropdown = await screen.findByRole('combobox', { name: 'Aggregation function' })
  await waitFor(() => expect(fnDropdown).toHaveAttribute('aria-expanded', 'true'))
  expect(screen.queryByRole('button', { name: /Edit then step/ })).toBeNull()
})

test('each added step becomes its own row, atop a persistent "then +" add row', async () => {
  renderSteps()
  await userEvent.click(screen.getByRole('button', { name: 'Add then step' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Add then step' }))

  // Two step rows plus the always-present add row: three "then" rows in total.
  expect(screen.getAllByRole('row')).toHaveLength(3)
  expect(screen.getAllByText('then')).toHaveLength(3)
})

test('removing a step drops it from the model', async () => {
  const { thenSteps } = renderSteps([{ id: 's1', function: 'sum', keys: [] }])
  await userEvent.click(screen.getByRole('button', { name: 'Remove then step' }))
  await waitFor(() => expect(thenSteps.value).toHaveLength(0))
})

test('the first step picks from the group-by keys', async () => {
  renderSteps()
  // Adding opens the step directly, so its "Add group key" button is available at once.
  await userEvent.click(screen.getByRole('button', { name: 'Add then step' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Add group key' }))

  // Let the empty-key auto-open (nextTick) settle so the click cannot re-toggle it.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = screen.getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  expect(await screen.findByRole('option', { name: 'service.name' })).toBeVisible()
  expect(screen.getByRole('option', { name: 'http.route' })).toBeVisible()
})

test('a later step draws its keys from the preceding step, not the group-by', async () => {
  // The predecessor groups by everything, so the second step cannot add a key.
  renderSteps([
    { id: 's1', function: 'sum', keys: [] },
    { id: 's2', function: 'avg', keys: [] }
  ])
  const chips = screen.getAllByRole('button', { name: /Edit then step/ })
  await userEvent.click(chips[1]!)
  await waitFor(() =>
    expect(screen.getByRole('combobox', { name: 'Aggregation function' })).toBeVisible()
  )
  expect(screen.queryByRole('button', { name: 'Add group key' })).toBeNull()
})
