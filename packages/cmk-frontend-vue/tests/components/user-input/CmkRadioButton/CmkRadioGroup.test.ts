/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import CmkRadioButton from '@/components/user-input/CmkRadioButton/CmkRadioButton.vue'
import CmkRadioGroup from '@/components/user-input/CmkRadioButton/CmkRadioGroup.vue'

test('CmkRadioGroup enforces mutual exclusion and updates its v-model on selection', async () => {
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      data: () => ({ modelValue: 'a' }),
      template: `
        <CmkRadioGroup v-model="modelValue">
          <CmkRadioButton value="a" label="Option A" />
          <CmkRadioButton value="b" label="Option B" />
        </CmkRadioGroup>
        <span data-testid="model">{{ modelValue }}</span>
      `
    })
  )

  const optionA = screen.getByRole('radio', { name: 'Option A' })
  const optionB = screen.getByRole('radio', { name: 'Option B' })
  expect(optionA).toHaveAttribute('aria-checked', 'true')
  expect(optionB).toHaveAttribute('aria-checked', 'false')
  expect(screen.getByTestId('model')).toHaveTextContent('a')

  await fireEvent.click(optionB)

  expect(optionA).toHaveAttribute('aria-checked', 'false')
  expect(optionB).toHaveAttribute('aria-checked', 'true')
  // The bound v-model is written back, not just reka-ui's internal aria state.
  expect(screen.getByTestId('model')).toHaveTextContent('b')
})

test('CmkRadioGroup disables every child and ignores clicks when disabled', async () => {
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      data: () => ({ modelValue: 'a' }),
      template: `
        <CmkRadioGroup v-model="modelValue" disabled>
          <CmkRadioButton value="a" label="Option A" />
          <CmkRadioButton value="b" label="Option B" />
        </CmkRadioGroup>
        <span data-testid="model">{{ modelValue }}</span>
      `
    })
  )

  const radios = screen.getAllByRole('radio')
  expect(radios[0]).toBeDisabled()
  expect(radios[1]).toBeDisabled()

  await fireEvent.click(radios[1]!)

  // Selection is unchanged because the group is disabled.
  expect(radios[0]).toHaveAttribute('aria-checked', 'true')
  expect(radios[1]).toHaveAttribute('aria-checked', 'false')
  expect(screen.getByTestId('model')).toHaveTextContent('a')
})

test('CmkRadioGroup renders updated validation', async () => {
  const { rerender } = render(CmkRadioGroup, {
    props: {
      externalErrors: ['some old validation']
    }
  })

  await rerender({
    externalErrors: ['some new validation']
  })

  await screen.findByText('some new validation')
})
