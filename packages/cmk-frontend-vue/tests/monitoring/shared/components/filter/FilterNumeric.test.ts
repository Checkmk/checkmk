/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterNumeric from '@/monitoring/shared/components/filter/FilterNumeric.vue'
import type { NumericFilter } from '@/monitoring/shared/components/filter/types'

const definition: NumericFilter<'num_services'> = {
  type: 'numeric',
  field: 'num_services',
  unit: 'services'
}

function renderFilter(initial: ColumnFilterNode<'num_services'> | undefined = undefined) {
  const model = ref<ColumnFilterNode<'num_services'> | undefined>(initial)
  render(
    defineComponent({
      components: { FilterNumeric },
      setup() {
        return { model, definition }
      },
      template: '<FilterNumeric v-model="model" :definition="definition" />'
    })
  )
  return { model }
}

test('both bounds produce an "and" of gte and lte conditions', async () => {
  const { model } = renderFilter()

  await userEvent.type(screen.getByRole('spinbutton', { name: 'From' }), '3')
  await userEvent.type(screen.getByRole('spinbutton', { name: 'To' }), '10')

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 3 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 10 }
    ]
  })
})

test('a lone lower bound produces a single gte condition', async () => {
  const { model } = renderFilter()

  await userEvent.type(screen.getByRole('spinbutton', { name: 'From' }), '1')

  expect(model.value).toEqual({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 1
  })
})

test('a lone upper bound produces a single lte condition', async () => {
  const { model } = renderFilter()

  await userEvent.type(screen.getByRole('spinbutton', { name: 'To' }), '5')

  expect(model.value).toEqual({
    type: 'condition',
    field: 'num_services',
    op: 'lte',
    value: 5
  })
})

test('an existing node is reflected back into the fields', () => {
  renderFilter({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 2 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 8 }
    ]
  })

  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(2)
  expect(screen.getByRole('spinbutton', { name: 'To' })).toHaveValue(8)
})

test('clearing both bounds removes the filter', async () => {
  const { model } = renderFilter({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 4
  })

  await userEvent.clear(screen.getByRole('spinbutton', { name: 'From' }))

  expect(model.value).toBeUndefined()
})

const withPresets: NumericFilter<'num_services_crit'> = {
  type: 'numeric',
  field: 'num_services_crit',
  presets: [
    { label: 'Any', from: 1 },
    { label: 'None', from: 0, to: 0 }
  ]
}

function renderWithPresets(initial: ColumnFilterNode<'num_services_crit'> | undefined = undefined) {
  const model = ref<ColumnFilterNode<'num_services_crit'> | undefined>(initial)
  render(
    defineComponent({
      components: { FilterNumeric },
      setup() {
        return { model, withPresets }
      },
      template: '<FilterNumeric v-model="model" :definition="withPresets" />'
    })
  )
  return { model }
}

test('no preset chips are rendered without a presets definition', () => {
  renderFilter()

  expect(screen.queryByRole('button', { name: 'Any' })).not.toBeInTheDocument()
})

test('selecting a preset chip prefills the range inputs', async () => {
  const { model } = renderWithPresets()

  await userEvent.click(screen.getByRole('button', { name: 'None' }))

  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(0)
  expect(screen.getByRole('spinbutton', { name: 'To' })).toHaveValue(0)
  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services_crit', op: 'gte', value: 0 },
      { type: 'condition', field: 'num_services_crit', op: 'lte', value: 0 }
    ]
  })
})

test('a single-bound preset prefills only the lower bound', async () => {
  const { model } = renderWithPresets()

  await userEvent.click(screen.getByRole('button', { name: 'Any' }))

  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(1)
  expect(screen.getByRole('spinbutton', { name: 'To' })).toHaveValue(null)
  expect(model.value).toEqual({
    type: 'condition',
    field: 'num_services_crit',
    op: 'gte',
    value: 1
  })
})

test('selecting the active preset chip again clears the filter', async () => {
  const { model } = renderWithPresets({
    type: 'condition',
    field: 'num_services_crit',
    op: 'gte',
    value: 1
  })

  expect(screen.getByRole('button', { name: 'Any' })).toHaveAttribute('aria-pressed', 'true')

  await userEvent.click(screen.getByRole('button', { name: 'Any' }))

  expect(model.value).toBeUndefined()
})

test('editing a prefilled bound deactivates the preset', async () => {
  const { model } = renderWithPresets({
    type: 'condition',
    field: 'num_services_crit',
    op: 'gte',
    value: 1
  })

  expect(screen.getByRole('button', { name: 'Any' })).toHaveAttribute('aria-pressed', 'true')

  await userEvent.type(screen.getByRole('spinbutton', { name: 'To' }), '5')

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services_crit', op: 'gte', value: 1 },
      { type: 'condition', field: 'num_services_crit', op: 'lte', value: 5 }
    ]
  })
  expect(screen.getByRole('button', { name: 'Any' })).toHaveAttribute('aria-pressed', 'false')
})
