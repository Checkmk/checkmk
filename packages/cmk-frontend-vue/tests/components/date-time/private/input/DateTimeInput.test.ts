/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { fireEvent, render } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type Ref, defineComponent, nextTick, shallowRef } from 'vue'

import DateTimeInput from '@/components/date-time/private/input/DateTimeInput.vue'
import type { DateTimePartsDraft, HourCycle } from '@/components/date-time/types'

import { DMY, MONTH_NAMES_EN } from '../../dateTimeTestFixtures'

// Render through a real parent host so the child's model stays shallow-reactive and the nested
// date/time payload keeps its original object identity when only one half changes.
const renderInput = (model: Ref<DateTimePartsDraft>, hourCycle: HourCycle = 24) =>
  render(
    defineComponent({
      components: { DateTimeInput },
      setup: () => ({ model, dateFormat: DMY, monthNames: MONTH_NAMES_EN, hourCycle }),
      template: `<DateTimeInput v-model="model" :date-format="dateFormat" :month-names="monthNames" :hour-cycle="hourCycle" />`
    })
  )

// DMY date field renders [day, month, year]; the time field renders [hour, minute(, meridiem)].
const dateInputs = (view: ReturnType<typeof renderInput>) =>
  Array.from(
    view.container.querySelectorAll<HTMLInputElement>('[role="group"][aria-label="Date"] input')
  )
const timeInputs = (view: ReturnType<typeof renderInput>) =>
  Array.from(
    view.container.querySelectorAll<HTMLInputElement>('[role="group"][aria-label="Time"] input')
  )

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DateTimeInput', () => {
  test('carry +1 advances the date', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 23, minute: 30 }
    })
    const time = model.value.time
    const view = renderInput(model)
    // ArrowUp on the hour crosses midnight (23 → 00), carrying +1 day into the date.
    await fireEvent.keyDown(timeInputs(view)[0]!, { key: 'ArrowUp' })

    expect(model.value.date).toEqual(new CalendarDate(2026, 3, 10))
    expect(model.value.time).toEqual(time)
  })

  test('carry with null date is a no-op', async () => {
    const model = shallowRef<DateTimePartsDraft>({ date: null, time: { hour: 23, minute: 30 } })
    const view = renderInput(model)
    await fireEvent.keyDown(timeInputs(view)[0]!, { key: 'ArrowUp' })

    expect(model.value.date).toBeNull()
  })

  test('carry crosses non-leap Feb', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2023, 2, 28),
      time: { hour: 23, minute: 30 }
    })
    const view = renderInput(model)
    await fireEvent.keyDown(timeInputs(view)[0]!, { key: 'ArrowUp' })

    expect(model.value.date).toEqual(new CalendarDate(2023, 3, 1))
  })

  test('editing the date leaves time alone', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const time = model.value.time
    const view = renderInput(model)
    // Step the day with an arrow (a complete date edit) and commit.
    await fireEvent.keyDown(dateInputs(view)[0]!, { key: 'ArrowUp' })

    expect(model.value.date).toEqual(new CalendarDate(2026, 3, 10))
    // The time half is forwarded by reference (spread of the same object), never re-derived.
    expect(model.value.time).toBe(time)
  })

  test('editing the time leaves date alone', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const date = model.value.date
    const view = renderInput(model)
    // Step the minute (a time edit that does not cross midnight).
    await fireEvent.keyDown(timeInputs(view)[1]!, { key: 'ArrowUp' })

    expect(model.value.time).toEqual({ hour: 8, minute: 6 })
    expect(model.value.date).toBe(date)
  })

  test('date navigate-out +1 → time', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const view = renderInput(model)
    const hour = timeInputs(view)[0]!
    const focus = vi.spyOn(hour, 'focus')
    // ArrowRight off the last date segment (year) relays focus into the time field.
    await fireEvent.keyDown(dateInputs(view)[2]!, { key: 'ArrowRight' })
    await nextTick()

    expect(focus).toHaveBeenCalled()
  })

  test('date navigate-out −1 stays', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const view = renderInput(model)
    const dateFocus = dateInputs(view).map((input) => vi.spyOn(input, 'focus'))
    const timeFocus = timeInputs(view).map((input) => vi.spyOn(input, 'focus'))
    // ArrowLeft off the first date segment (day): the date field only relays +1, so −1 is a no-op.
    await fireEvent.keyDown(dateInputs(view)[0]!, { key: 'ArrowLeft' })
    await nextTick()

    for (const spy of [...dateFocus, ...timeFocus]) {
      expect(spy).not.toHaveBeenCalled()
    }
  })

  test('time navigate-out −1 → date last', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const view = renderInput(model)
    const year = dateInputs(view)[2]!
    const focus = vi.spyOn(year, 'focus')
    // ArrowLeft off the first time segment (hour) relays focus back to the date field's last segment.
    await fireEvent.keyDown(timeInputs(view)[0]!, { key: 'ArrowLeft' })
    await nextTick()

    expect(focus).toHaveBeenCalled()
  })

  test('time navigate-out +1 stays', async () => {
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const view = renderInput(model)
    const dateFocus = dateInputs(view).map((input) => vi.spyOn(input, 'focus'))
    const timeFocus = timeInputs(view).map((input) => vi.spyOn(input, 'focus'))
    // ArrowRight off the last time segment (minute): the time field only relays −1, so +1 is a no-op.
    await fireEvent.keyDown(timeInputs(view)[1]!, { key: 'ArrowRight' })
    await nextTick()

    for (const spy of [...dateFocus, ...timeFocus]) {
      expect(spy).not.toHaveBeenCalled()
    }
  })

  test('non-trigger mode exposes no popup-opening button', () => {
    // The range picker reuses this input inside an already-open flyout: with asTrigger off the
    // (decorative) icon is not a button, so there is no popup-opening affordance here.
    const model = shallowRef<DateTimePartsDraft>({
      date: new CalendarDate(2026, 3, 9),
      time: { hour: 8, minute: 5 }
    })
    const view = renderInput(model)
    expect(view.queryByRole('button', { name: 'Open calendar' })).toBeNull()
  })
})
