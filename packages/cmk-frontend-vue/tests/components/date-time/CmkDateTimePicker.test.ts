/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  CalendarDate,
  CalendarDateTime,
  type ZonedDateTime,
  toZoned
} from '@internationalized/date'
import * as intl from '@internationalized/date'
import { fireEvent } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import CmkDateTimePicker from '@/components/date-time/CmkDateTimePicker.vue'
import type { DateTimePickerSettings } from '@/components/date-time/types'

import { TZ_UTC } from './dateTimeTestFixtures'
import { lastValue, renderModelPicker } from './pickerTestHarness'

// Mock `today` so a null-model calendar opens on a known month (June 2026).
vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, today: vi.fn(actual.today), getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

const SETTINGS: DateTimePickerSettings = {
  hourCycle: 24,
  dateFormat: 'iso',
  firstDayOfWeek: 1,
  weekendDays: [0, 6]
}

const utc = (
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number
): ZonedDateTime =>
  toZoned(new CalendarDateTime(year, month, day, hour, minute), TZ_UTC, 'compatible')

const renderPicker = (model: ZonedDateTime | null, props: Record<string, unknown> = {}) =>
  renderModelPicker<ZonedDateTime | null>(CmkDateTimePicker, model, {
    settings: SETTINGS,
    timeZone: TZ_UTC,
    ...props
  })

type PickerView = ReturnType<typeof renderPicker>

const openCalendar = (view: PickerView) =>
  fireEvent.click(view.getByRole('button', { name: 'Open calendar' }))
// Day buttons are named by their full date ("June 20, 2026"); anchor on "<day>," which is
// unambiguous (adjacent-month days are not buttons, so each in-month day number is unique).
const clickDay = (view: PickerView, day: string) =>
  fireEvent.click(view.getByRole('button', { name: new RegExp(`\\b${day},`) }))
const apply = (view: PickerView) => fireEvent.click(view.getByRole('button', { name: 'Apply' }))
const pad = (value: number) => value.toString().padStart(2, '0')

async function setTime(view: PickerView, hour: number, minute: number): Promise<void> {
  await fireEvent.update(view.getByRole('spinbutton', { name: 'Hours' }), pad(hour))
  await fireEvent.update(view.getByRole('spinbutton', { name: 'Minutes' }), pad(minute))
  await nextTick()
}

beforeEach(() => {
  vi.mocked(intl.today).mockReturnValue(new CalendarDate(2026, 6, 10))
  vi.mocked(intl.getLocalTimeZone).mockReturnValue(TZ_UTC)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CmkDateTimePicker', () => {
  test('editing only the date preserves the time of day', async () => {
    const view = renderPicker(utc(2026, 6, 10, 8, 45))
    await openCalendar(view)
    await clickDay(view, '20')
    await apply(view)

    const committed = lastValue(view.updates)!
    expect(committed.toString()).toContain('2026-06-20')
    expect(committed.hour).toBe(8)
    expect(committed.minute).toBe(45)
  })

  test('non-nullable requires a complete date & time — Apply is disabled while empty', async () => {
    const view = renderPicker(null, { nullable: false })
    await openCalendar(view)
    expect(view.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })

  test('a staged date still needs a time', async () => {
    const view = renderPicker(null, { nullable: false })
    await openCalendar(view)
    await clickDay(view, '15')
    expect(view.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })

  test('a complete staged date-time enables Apply and commits the chosen time', async () => {
    const view = renderPicker(null, { nullable: false })
    await openCalendar(view)
    await clickDay(view, '15')
    await setTime(view, 8, 30)
    expect(view.getByRole('button', { name: 'Apply' })).toBeEnabled()

    await apply(view)
    const committed = lastValue(view.updates)!
    expect(committed.toString()).toContain('2026-06-15')
    expect(committed.hour).toBe(8)
    expect(committed.minute).toBe(30)
  })

  test('Enter in the trigger runs the save handler, then commits and closes', async () => {
    const saveHandler = vi.fn(() => true)
    const view = renderPicker(utc(2026, 6, 10, 8, 45), { saveMode: true, saveHandler })
    await openCalendar(view)
    await clickDay(view, '20')
    await fireEvent.click(view.getByRole('checkbox'))
    // Enter on the first trigger segment is the same apply path as the footer "Save & apply".
    await fireEvent.keyDown(view.getByRole('spinbutton', { name: 'Day' }), {
      key: 'Enter'
    })
    await nextTick()

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(lastValue(view.updates)!.toString()).toContain('2026-06-20')
    expect(view.currentOpen()).toBe(false)
  })

  test('announces "Saving…" while the save handler is in flight', async () => {
    // Wiring guard: the picker forwards pendingSave so the footer can announce the in-flight save.
    const saveHandler = vi.fn(() => new Promise<boolean>(() => {}))
    const view = renderPicker(utc(2026, 6, 10, 8, 45), { saveMode: true, saveHandler })
    await openCalendar(view)
    await fireEvent.click(view.getByRole('checkbox'))
    await fireEvent.click(view.getByRole('button', { name: 'Save & apply' }))
    await nextTick()

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(view.getByText('Saving…')).toBeInTheDocument()
  })
})
