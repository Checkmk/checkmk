/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import CmkTimePicker from '@/components/CmkDateTimePicker/CmkTimePicker.vue'

test('CmkTimePicker renders initial time value', () => {
  render(CmkTimePicker, {
    props: { modelValue: '14:30' }
  })

  const hoursInput = screen.getByRole('textbox', { name: 'Hours' })
  const minutesInput = screen.getByRole('textbox', { name: 'Minutes' })
  expect(hoursInput).toHaveValue('14')
  expect(minutesInput).toHaveValue('30')
})

test('CmkTimePicker defaults to 00:00 for invalid input', () => {
  render(CmkTimePicker, {
    props: { modelValue: 'invalid' }
  })

  const hoursInput = screen.getByRole('textbox', { name: 'Hours' })
  const minutesInput = screen.getByRole('textbox', { name: 'Minutes' })
  expect(hoursInput).toHaveValue('00')
  expect(minutesInput).toHaveValue('00')
})

test('CmkTimePicker emits update on arrow key up in hours', async () => {
  const wrapper = defineComponent({
    components: { CmkTimePicker },
    setup() {
      const time = ref('10:30')
      return { time }
    },
    template: `<CmkTimePicker v-model="time" />`
  })
  render(wrapper)

  const hoursInput = screen.getByRole('textbox', { name: 'Hours' })
  await fireEvent.keyDown(hoursInput, { key: 'ArrowUp' })

  expect(hoursInput).toHaveValue('11')
})

test('CmkTimePicker wraps hours from 23 to 0 on arrow up', async () => {
  const wrapper = defineComponent({
    components: { CmkTimePicker },
    setup() {
      const time = ref('23:00')
      return { time }
    },
    template: `<CmkTimePicker v-model="time" />`
  })
  render(wrapper)

  const hoursInput = screen.getByRole('textbox', { name: 'Hours' })
  await fireEvent.keyDown(hoursInput, { key: 'ArrowUp' })

  expect(hoursInput).toHaveValue('00')
})

test('CmkTimePicker keyboard input accepts two-digit hours', async () => {
  const wrapper = defineComponent({
    components: { CmkTimePicker },
    setup() {
      const time = ref('00:00')
      return { time }
    },
    template: `<CmkTimePicker v-model="time" />`
  })
  render(wrapper)

  const hoursInput = screen.getByRole('textbox', { name: 'Hours' })
  await userEvent.clear(hoursInput)
  await userEvent.type(hoursInput, '10')

  expect(hoursInput).toHaveValue('10')
})

test('CmkTimePicker has accessible trigger button', () => {
  render(CmkTimePicker, {
    props: { modelValue: '12:00' }
  })

  screen.getByRole('button', { name: 'Open time picker' })
})

test('CmkTimePicker popup opens on trigger click', async () => {
  render(CmkTimePicker, {
    props: { modelValue: '12:00' }
  })

  const trigger = screen.getByRole('button', { name: 'Open time picker' })
  await fireEvent.click(trigger)

  expect(screen.getByText('H')).toBeInTheDocument()
  expect(screen.getByText('M')).toBeInTheDocument()
})

test('CmkTimePicker updates value on popup hour selection', async () => {
  const wrapper = defineComponent({
    components: { CmkTimePicker },
    setup() {
      const time = ref('05:30')
      return { time }
    },
    template: `<CmkTimePicker v-model="time" />`
  })
  render(wrapper)

  const trigger = screen.getByRole('button', { name: 'Open time picker' })
  await fireEvent.click(trigger)

  const buttons = screen.getAllByRole('button')
  const hour14Button = buttons.find((b) => b.textContent?.trim() === '14')
  expect(hour14Button).toBeDefined()
  await fireEvent.click(hour14Button!)

  const hoursInput = screen.getByRole('textbox', { name: 'Hours' })
  expect(hoursInput).toHaveValue('14')
})
