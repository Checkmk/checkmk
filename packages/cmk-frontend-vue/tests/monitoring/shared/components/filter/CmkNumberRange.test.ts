/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import CmkNumberRange, {
  type NumberRange
} from '@/monitoring/shared/components/filter/CmkNumberRange.vue'

test('CmkNumberRange labels both bounds with the defaults', () => {
  render(CmkNumberRange)

  screen.getByRole('spinbutton', { name: 'From' })
  screen.getByRole('spinbutton', { name: 'To' })
})

test('CmkNumberRange uses custom bound labels', () => {
  render(CmkNumberRange, { props: { fromLabel: 'At least', toLabel: 'At most' } })

  screen.getByRole('spinbutton', { name: 'At least' })
  screen.getByRole('spinbutton', { name: 'At most' })
})

test('CmkNumberRange updates the model on input', async () => {
  const model = ref<NumberRange>({ from: undefined, to: undefined })
  render(
    defineComponent({
      components: { CmkNumberRange },
      setup() {
        return { model }
      },
      template: '<CmkNumberRange v-model="model" />'
    })
  )

  await userEvent.type(screen.getByRole('spinbutton', { name: 'From' }), '3')
  await userEvent.type(screen.getByRole('spinbutton', { name: 'To' }), '10')

  expect(model.value).toEqual({ from: 3, to: 10 })
})

test('CmkNumberRange flags a lower bound above the upper bound', async () => {
  render(CmkNumberRange, { props: { modelValue: { from: 10, to: 3 } } })

  expect(
    await screen.findByText('The lower bound must not exceed the upper bound.')
  ).toBeInTheDocument()
})

test('CmkNumberRange accepts an open upper bound without error', () => {
  render(CmkNumberRange, { props: { modelValue: { from: 1, to: undefined } } })

  expect(
    screen.queryByText('The lower bound must not exceed the upper bound.')
  ).not.toBeInTheDocument()
})

test('CmkNumberRange clears a bound back to undefined when emptied', async () => {
  const model = ref<NumberRange>({ from: 3, to: 10 })
  render(
    defineComponent({
      components: { CmkNumberRange },
      setup() {
        return { model }
      },
      template: '<CmkNumberRange v-model="model" />'
    })
  )

  await userEvent.clear(screen.getByRole('spinbutton', { name: 'From' }))

  expect(model.value).toEqual({ from: undefined, to: 10 })
})
