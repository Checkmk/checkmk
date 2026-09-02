/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import OtpInput from '@/otp-input/OtpInput.vue'

function digits(): HTMLInputElement[] {
  return screen.getAllByRole('textbox') as HTMLInputElement[]
}

function values(): string[] {
  return digits().map((input) => input.value)
}

test('OtpInput renders six labelled digits', () => {
  render(OtpInput)

  expect(digits()).toHaveLength(6)
  expect(screen.getByLabelText('Digit 1 of 6')).toBeInTheDocument()
  expect(screen.getByLabelText('Digit 6 of 6')).toBeInTheDocument()
})

test('OtpInput advances focus while typing and collects the code', async () => {
  const { emitted } = render(OtpInput)

  await userEvent.type(digits()[0]!, '424242')

  expect(values()).toEqual(['4', '2', '4', '2', '4', '2'])
  expect(emitted()['update:modelValue']?.at(-1)).toEqual(['424242'])
})

test('OtpInput keeps non-digits out of the boxes', async () => {
  render(OtpInput)

  await userEvent.type(digits()[0]!, 'a1b2')

  // The letters are dropped outright; focus only moves on an accepted digit, so the two
  // digits land in the first two boxes.
  expect(values()).toEqual(['1', '2', '', '', '', ''])
})

test('OtpInput submits once the last digit completes the code', async () => {
  const { emitted } = render(OtpInput)

  await userEvent.type(digits()[0]!, '42424')
  expect(emitted()['submit']).toBeUndefined()

  await userEvent.type(digits()[5]!, '2')
  expect(emitted()['submit']).toHaveLength(1)
})

test('OtpInput splits a pasted code across the boxes and submits', async () => {
  const { emitted } = render(OtpInput)

  await userEvent.click(digits()[0]!)
  await userEvent.paste('424242')

  expect(values()).toEqual(['4', '2', '4', '2', '4', '2'])
  expect(emitted()['submit']).toHaveLength(1)
})

test('OtpInput strips separators from a pasted code and does not submit a partial one', async () => {
  const { emitted } = render(OtpInput)

  await userEvent.click(digits()[0]!)
  await userEvent.paste('42-42')

  expect(values()).toEqual(['4', '2', '4', '2', '', ''])
  expect(emitted()['submit']).toBeUndefined()
})

test('OtpInput clears the current digit on backspace, then walks left', async () => {
  render(OtpInput)

  await userEvent.type(digits()[0]!, '4242')
  expect(document.activeElement).toBe(digits()[4])

  // The box under the cursor is empty, so the first press clears the one before it.
  await userEvent.keyboard('{Backspace}')
  expect(values()).toEqual(['4', '2', '4', '', '', ''])
  expect(document.activeElement).toBe(digits()[3])

  // That box is empty again, so the next press repeats the walk one place further left.
  await userEvent.keyboard('{Backspace}')
  expect(values()).toEqual(['4', '2', '', '', '', ''])
  expect(document.activeElement).toBe(digits()[2])
})

test('OtpInput leaves the other digits alone when a middle one is cleared', async () => {
  render(OtpInput)

  await userEvent.type(digits()[0]!, '424242')

  await userEvent.click(digits()[1]!)
  await userEvent.keyboard('{Backspace}')

  expect(values()).toEqual(['4', '', '4', '2', '4', '2'])
})

test('OtpInput moves focus with the arrow keys', async () => {
  render(OtpInput)

  await userEvent.click(digits()[2]!)

  await userEvent.keyboard('{ArrowRight}')
  expect(document.activeElement).toBe(digits()[3])

  await userEvent.keyboard('{ArrowLeft}')
  expect(document.activeElement).toBe(digits()[2])
})

test('OtpInput fills the boxes from the model', () => {
  render(OtpInput, { props: { modelValue: '135' } })

  expect(values()).toEqual(['1', '3', '5', '', '', ''])
})

test('OtpInput disables every digit when disabled', () => {
  render(OtpInput, { props: { disabled: true } })

  expect(digits().every((input) => input.disabled)).toBe(true)
})

test('OtpInput marks every digit when in error', () => {
  render(OtpInput, { props: { error: true } })

  expect(digits().every((input) => input.classList.contains('otp-input__digit--error'))).toBe(true)
})

test('OtpInput exposes focus, which lands on the first digit', async () => {
  render(
    defineComponent({
      components: { OtpInput },
      setup() {
        const otp = ref<InstanceType<typeof OtpInput> | null>(null)
        return { otp, focusCode: () => otp.value?.focus() }
      },
      template: `
        <OtpInput ref="otp" />
        <button @click="focusCode">focus the code</button>
      `
    })
  )

  await userEvent.click(screen.getByRole('button', { name: 'focus the code' }))

  expect(document.activeElement).toBe(digits()[0])
})
