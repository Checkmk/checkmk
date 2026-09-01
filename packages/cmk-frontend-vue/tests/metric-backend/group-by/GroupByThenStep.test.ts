/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import GroupByThenStep from '@/metric-backend/group-by/GroupByThenStep.vue'
import type { AggregationStep, GroupKey } from '@/metric-backend/group-by/types'

const ALLOWED: GroupKey[] = [
  { id: 'a', attributeKind: 'resource', attributeKey: 'service.name' },
  { id: 'b', attributeKind: 'data_point', attributeKey: 'http.route' }
]

function renderStep(step: Partial<AggregationStep> = {}, allowedKeys: GroupKey[] = ALLOWED) {
  const model = ref<AggregationStep>({ id: 's', function: 'avg', keys: [], ...step })
  const wrapper = defineComponent({
    components: { GroupByThenStep },
    setup() {
      return {
        model,
        allowedKeys,
        onUpdate: (value: AggregationStep) => {
          model.value = value
        }
      }
    },
    template: `
      <GroupByThenStep
        :model-value="model"
        :allowed-keys="allowedKeys"
        @update:model-value="onUpdate"
      />
    `
  })
  render(wrapper)
  return { model }
}

async function openStep(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: /Edit then step/ }))
}

test('the collapsed chip summarises "<function> nothing, combine all series into one" with no keys', () => {
  renderStep({ function: 'avg', keys: [] })
  const chip = screen.getByRole('button', { name: /Edit then step/ })
  // The pill no longer carries the "then" word; that lives in the row label beside it.
  expect(chip).not.toHaveTextContent('then')
  expect(chip).toHaveTextContent('avg by')
  expect(chip).toHaveTextContent('nothing, combine all series into one')
})

test.each([
  { scenario: 'the preceding step groups by everything', allowedKeys: [], shown: false },
  { scenario: 'the preceding step defines keys', allowedKeys: ALLOWED, shown: true }
])('the add-key button shows only when $scenario', async ({ allowedKeys, shown }) => {
  renderStep({ function: 'sum', keys: [] }, allowedKeys)
  await openStep()
  expect(screen.queryByRole('button', { name: 'Add group key' }) === null).toBe(!shown)
})

test('the remove button shows on the collapsed chip but is hidden while editing', async () => {
  renderStep({ function: 'avg', keys: [] })
  expect(screen.getByRole('button', { name: 'Remove then step' })).toBeVisible()

  await openStep()
  expect(screen.queryByRole('button', { name: 'Remove then step' })).toBeNull()
})

test('the key picker is restricted to the preceding step keys and derives the kind', async () => {
  const { model } = renderStep({ function: 'sum', keys: [] }, ALLOWED)
  await openStep()

  await userEvent.click(screen.getByRole('button', { name: 'Add group key' }))
  await waitFor(() => expect(model.value.keys).toHaveLength(1))

  // Let the empty-key auto-open (nextTick) settle so the click cannot re-toggle it.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = screen.getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }

  expect(await screen.findByRole('option', { name: 'service.name' })).toBeVisible()
  expect(screen.getByRole('option', { name: 'http.route' })).toBeVisible()

  await userEvent.click(screen.getByRole('option', { name: 'http.route' }))
  await waitFor(() => expect(model.value.keys[0]!.attributeKey).toBe('http.route'))
  expect(model.value.keys[0]!.attributeKind).toBe('data_point')
})

test('the collapsed chip is a tab stop wrapping the chip and the remove X, opening on Enter', async () => {
  renderStep({ function: 'avg', keys: [] })

  await userEvent.tab()
  const stop = within(document.activeElement as HTMLElement)
  expect(stop.getByRole('button', { name: /Edit then step/ })).toBeInTheDocument()
  expect(stop.getByRole('button', { name: 'Remove then step' })).toBeInTheDocument()

  await userEvent.keyboard('{Enter}')
  expect(screen.getByRole('combobox', { name: 'Aggregation function' })).toBeVisible()
})
