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

test('selecting "Any (>0)" applies a lone lower bound of 1', async () => {
  const { model } = renderFilter()

  await userEvent.click(screen.getByRole('radio', { name: 'Any (>0)' }))

  expect(model.value).toEqual({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 1
  })
})

test('selecting "None (=0)" applies a 0-to-0 range', async () => {
  const { model } = renderFilter()

  await userEvent.click(screen.getByRole('radio', { name: 'None (=0)' }))

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 0 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 0 }
    ]
  })
})

test('the range inputs are disabled until the "Range" radio is selected', async () => {
  renderFilter()

  expect(screen.getByRole('spinbutton', { name: 'From' })).toBeDisabled()

  await userEvent.click(screen.getByRole('radio', { name: 'Range' }))

  expect(screen.getByRole('spinbutton', { name: 'From' })).toBeEnabled()
})

test('both bounds produce an "and" of gte and lte conditions', async () => {
  const { model } = renderFilter()

  await userEvent.click(screen.getByRole('radio', { name: 'Range' }))
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

  await userEvent.click(screen.getByRole('radio', { name: 'Range' }))
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

  await userEvent.click(screen.getByRole('radio', { name: 'Range' }))
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

  expect(screen.getByRole('radio', { name: 'Range' })).toBeChecked()
  expect(screen.getByRole('spinbutton', { name: 'From' })).toHaveValue(2)
  expect(screen.getByRole('spinbutton', { name: 'To' })).toHaveValue(8)
})

test('an existing lone gte of 1 pre-selects "Any (>0)"', () => {
  renderFilter({
    type: 'condition',
    field: 'num_services',
    op: 'gte',
    value: 1
  })

  expect(screen.getByRole('radio', { name: 'Any (>0)' })).toBeChecked()
  expect(screen.getByRole('spinbutton', { name: 'From' })).toBeDisabled()
})

test('an existing 0-to-0 range pre-selects "None (=0)"', () => {
  renderFilter({
    type: 'and',
    children: [
      { type: 'condition', field: 'num_services', op: 'gte', value: 0 },
      { type: 'condition', field: 'num_services', op: 'lte', value: 0 }
    ]
  })

  expect(screen.getByRole('radio', { name: 'None (=0)' })).toBeChecked()
})
