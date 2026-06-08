/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import CmkDeprecatedDateTimePicker from '@/components/CmkDeprecatedDateTimePicker/CmkDeprecatedDateTimePicker.vue'

test('CmkDeprecatedDateTimePicker renders date and time in datetime mode', () => {
  render(
    defineComponent({
      components: { CmkDeprecatedDateTimePicker },
      setup() {
        const date = ref('2026-03-15')
        const time = ref('14:30')
        return { date, time }
      },
      template: `<CmkDeprecatedDateTimePicker v-model:date="date" v-model:time="time" mode="datetime" />`
    })
  )

  expect(screen.getByRole('textbox', { name: 'Hours' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Open calendar' })).toBeInTheDocument()
})

test('CmkDeprecatedDateTimePicker renders only date in date mode', () => {
  render(
    defineComponent({
      components: { CmkDeprecatedDateTimePicker },
      setup() {
        const date = ref('2026-03-15')
        const time = ref('00:00')
        return { date, time }
      },
      template: `<CmkDeprecatedDateTimePicker v-model:date="date" v-model:time="time" mode="date" />`
    })
  )

  expect(screen.getByRole('button', { name: 'Open calendar' })).toBeInTheDocument()
  expect(screen.queryByRole('textbox', { name: 'Hours' })).not.toBeInTheDocument()
})

test('CmkDeprecatedDateTimePicker renders only time in time mode', () => {
  render(
    defineComponent({
      components: { CmkDeprecatedDateTimePicker },
      setup() {
        const date = ref('')
        const time = ref('14:30')
        return { date, time }
      },
      template: `<CmkDeprecatedDateTimePicker v-model:date="date" v-model:time="time" mode="time" />`
    })
  )

  expect(screen.getByRole('textbox', { name: 'Hours' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Open calendar' })).not.toBeInTheDocument()
})

test('CmkDeprecatedDateTimePicker displays suffix text', () => {
  render(
    defineComponent({
      components: { CmkDeprecatedDateTimePicker },
      setup() {
        const date = ref('2026-03-15')
        const time = ref('14:30')
        return { date, time }
      },
      template: `<CmkDeprecatedDateTimePicker v-model:date="date" v-model:time="time" suffix="UTC+1" />`
    })
  )

  expect(screen.getByText('UTC+1')).toBeInTheDocument()
})

test('CmkDeprecatedDateTimePicker opens calendar on trigger click', async () => {
  render(
    defineComponent({
      components: { CmkDeprecatedDateTimePicker },
      setup() {
        const date = ref('2026-03-15')
        const time = ref('14:30')
        return { date, time }
      },
      template: `<CmkDeprecatedDateTimePicker v-model:date="date" v-model:time="time" mode="date" />`
    })
  )

  const trigger = screen.getByRole('button', { name: 'Open calendar' })
  await fireEvent.click(trigger)

  expect(screen.getByRole('button', { name: 'Previous month' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Next month' })).toBeInTheDocument()
})

test('CmkDeprecatedDateTimePicker defaults to datetime mode', () => {
  render(
    defineComponent({
      components: { CmkDeprecatedDateTimePicker },
      setup() {
        const date = ref('2026-03-15')
        const time = ref('14:30')
        return { date, time }
      },
      template: `<CmkDeprecatedDateTimePicker v-model:date="date" v-model:time="time" />`
    })
  )

  expect(screen.getByRole('button', { name: 'Open calendar' })).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: 'Hours' })).toBeInTheDocument()
})
