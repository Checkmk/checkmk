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

test('the option group is reachable by name', () => {
  renderFilter()

  expect(screen.getByRole('group', { name: 'Value range' })).toBeInTheDocument()
})

test('selecting "At least one" applies a lone lower bound of 1', async () => {
  const { model } = renderFilter()

  await userEvent.click(screen.getByRole('button', { name: 'Toggle At least one' }))

  expect(model.value).toEqual({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 1
  })
})

test('selecting "None" applies a 0-to-0 range', async () => {
  const { model } = renderFilter()

  await userEvent.click(screen.getByRole('button', { name: 'Toggle None' }))

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 0 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 0 }
    ]
  })
})

test('a column says in its own words what a preset matches', async () => {
  const model = ref<ColumnFilterNode<'num_services'> | undefined>(undefined)
  const described: NumericFilter<'num_services'> = {
    ...definition,
    anyInfo: 'Shows hosts with at least one service.'
  }
  render(
    defineComponent({
      components: { FilterNumeric },
      setup() {
        return { model, definition: described }
      },
      template: '<FilterNumeric v-model="model" :definition="definition" />'
    })
  )

  await userEvent.click(screen.getByRole('button', { name: 'Toggle At least one' }))

  expect(screen.getByText('Shows hosts with at least one service.')).toBeInTheDocument()
})

test('a preset replaces the range inputs with what it matches', async () => {
  renderFilter()

  expect(screen.getByRole('spinbutton', { name: 'From' })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Toggle None' }))

  expect(screen.queryByRole('spinbutton', { name: 'From' })).not.toBeInTheDocument()
  expect(screen.getByText('Shows rows with a value of 0.')).toBeInTheDocument()
})

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

test('an existing custom range pre-selects "Range" and reflects the bounds', () => {
  renderFilter({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 2 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 8 }
    ]
  })

  expect(screen.getByRole('button', { name: 'Toggle Range' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(2)
  expect(screen.getByRole('spinbutton', { name: 'To' })).toHaveValue(8)
})

test('an existing lone gte of 1 pre-selects "At least one"', () => {
  renderFilter({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 1
  })

  expect(screen.getByRole('button', { name: 'Toggle At least one' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.queryByRole('spinbutton', { name: 'From' })).not.toBeInTheDocument()
})

test('an existing 0-to-0 range pre-selects "None"', () => {
  renderFilter({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 0 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 0 }
    ]
  })

  expect(screen.getByRole('button', { name: 'Toggle None' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
})
