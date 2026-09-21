/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { type Ref, defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterDuration from '@/monitoring/shared/components/filter/FilterDuration.vue'
import type { DurationFilter } from '@/monitoring/shared/components/filter/types'

const definition: DurationFilter<'last_state_change'> = {
  type: 'duration',
  field: 'last_state_change'
}

type Exposed = { validate: () => boolean }

function renderFilter(initial: ColumnFilterNode<'last_state_change'> | undefined = undefined) {
  const model = ref<ColumnFilterNode<'last_state_change'> | undefined>(initial)
  const filter = ref<Exposed | null>(null)
  render(
    defineComponent({
      components: { FilterDuration },
      setup() {
        return { model, definition, filter }
      },
      template: '<FilterDuration ref="filter" v-model="model" :definition="definition" />'
    })
  )
  return { model, filter: filter as Ref<Exposed | null> }
}

const user = userEvent.setup()

test('"Less than" caps the age', async () => {
  const { model } = renderFilter()

  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '5')

  expect(model.value).toEqual({
    type: 'age',
    field: 'last_state_change',
    op: 'younger_than',
    seconds: 5 * 60
  })
})

test('"More than" floors the age', async () => {
  const { model } = renderFilter()

  await user.click(screen.getByRole('button', { name: 'Toggle More than' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '2')

  expect(model.value).toEqual({
    type: 'age',
    field: 'last_state_change',
    op: 'older_than',
    seconds: 2 * 60
  })
})

test('a span bounds the age on both sides', async () => {
  const { model } = renderFilter()

  await user.click(screen.getByRole('button', { name: 'Toggle Between' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Younger bound' }), '5')
  await user.type(screen.getByRole('spinbutton', { name: 'Older bound' }), '30')

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'age', field: 'last_state_change', op: 'older_than', seconds: 5 * 60 },
      { type: 'age', field: 'last_state_change', op: 'younger_than', seconds: 30 * 60 }
    ]
  })
})

test('a number entered survives switching between the single-bound toggles', async () => {
  const { model } = renderFilter()

  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '7')
  await user.click(screen.getByRole('button', { name: 'Toggle More than' }))

  expect(screen.getByRole('spinbutton', { name: 'Age' })).toHaveValue(7)
  expect(model.value).toEqual({
    type: 'age',
    field: 'last_state_change',
    op: 'older_than',
    seconds: 7 * 60
  })
})

test('a number entered survives switching to a span', async () => {
  renderFilter()

  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '7')
  await user.click(screen.getByRole('button', { name: 'Toggle Between' }))

  expect(screen.getByRole('spinbutton', { name: 'Younger bound' })).toHaveValue(7)
})

test('a number is read in the new unit rather than converted into it', async () => {
  const { model } = renderFilter()

  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '5')
  await user.click(screen.getByRole('combobox', { name: 'Unit' }))
  await user.click(screen.getByRole('option', { name: 'hours' }))

  expect(screen.getByRole('spinbutton', { name: 'Age' })).toHaveValue(5)
  expect(model.value).toEqual({
    type: 'age',
    field: 'last_state_change',
    op: 'younger_than',
    seconds: 5 * 3600
  })
})

test('an inverted span is refused, and only once it is committed', async () => {
  const { filter } = renderFilter()

  await user.click(screen.getByRole('button', { name: 'Toggle Between' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Younger bound' }), '30')

  expect(
    screen.queryByText('Enter a younger bound that does not exceed the older one.')
  ).not.toBeInTheDocument()

  await user.type(screen.getByRole('spinbutton', { name: 'Older bound' }), '5')

  expect(filter.value!.validate()).toBe(false)
  expect(
    await screen.findByText('Enter a younger bound that does not exceed the older one.')
  ).toBeInTheDocument()
})

test('an age in the future is refused', async () => {
  const { filter } = renderFilter()

  await user.type(screen.getByRole('spinbutton', { name: 'Age' }), '-5')

  expect(filter.value!.validate()).toBe(false)
  expect(await screen.findByText('Enter an age of zero or more.')).toBeInTheDocument()
})

test('an existing older-than bound reopens as "More than"', () => {
  renderFilter({
    type: 'age',
    field: 'last_state_change',
    op: 'older_than',
    seconds: 3 * 3600
  })

  expect(screen.getByRole('button', { name: 'Toggle More than' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.getByRole('spinbutton', { name: 'Age' })).toHaveValue(3)
})

test('a span reopens in the coarsest unit both of its bounds divide by', () => {
  renderFilter({
    type: 'and',
    children: [
      { type: 'age', field: 'last_state_change', op: 'older_than', seconds: 3600 },
      { type: 'age', field: 'last_state_change', op: 'younger_than', seconds: 5400 }
    ]
  })

  expect(screen.getByRole('spinbutton', { name: 'Younger bound' })).toHaveValue(60)
  expect(screen.getByRole('spinbutton', { name: 'Older bound' })).toHaveValue(90)
})
