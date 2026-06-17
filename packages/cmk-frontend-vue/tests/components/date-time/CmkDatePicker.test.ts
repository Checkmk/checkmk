/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import * as intl from '@internationalized/date'
import { fireEvent, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import CmkDatePicker from '@/components/date-time/CmkDatePicker.vue'
import type { DateTimePickerSettings } from '@/components/date-time/types'

import { TZ_TOKYO, TZ_UTC } from './dateTimeTestFixtures'
import { lastValue, renderModelPicker } from './pickerTestHarness'

// Mock `today` so the calendar always opens on a known month (June 2026) and clicking a day yields
// a deterministic date.
vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, today: vi.fn(actual.today), getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

// ISO date format so the rendered segments never depend on the host locale.
const SETTINGS: DateTimePickerSettings = {
  hourCycle: 24,
  dateFormat: 'iso',
  firstDayOfWeek: 1,
  weekendDays: [0, 6]
}

const renderPicker = (model: CalendarDate | null, props: Record<string, unknown> = {}) =>
  renderModelPicker<CalendarDate | null>(CmkDatePicker, model, {
    settings: SETTINGS,
    timeZone: TZ_UTC,
    ...props
  })

type PickerView = ReturnType<typeof renderPicker>

const openCalendar = (view: PickerView) =>
  fireEvent.click(view.getByRole('button', { name: 'Open calendar' }))
// Day buttons are named by their full date ("June 15, 2026"); anchor on "<day>," which is
// unambiguous (adjacent-month days are not buttons, so each in-month day number is unique).
const clickDay = (view: PickerView, day: string) =>
  fireEvent.click(view.getByRole('button', { name: new RegExp(`\\b${day},`) }))
const apply = (view: PickerView) => fireEvent.click(view.getByRole('button', { name: 'Apply' }))

beforeEach(() => {
  vi.mocked(intl.today).mockReturnValue(new CalendarDate(2026, 6, 10))
  vi.mocked(intl.getLocalTimeZone).mockReturnValue(TZ_UTC)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CmkDatePicker', () => {
  test('picking a day in the calendar and applying emits that date', async () => {
    const view = renderPicker(null, { nullable: true })
    await openCalendar(view)
    await clickDay(view, '15')
    await apply(view)
    expect(lastValue(view.updates)!.toString()).toBe('2026-06-15')
  })

  test('non-nullable disables Apply while no date is staged', async () => {
    const view = renderPicker(null, { nullable: false })
    await openCalendar(view)
    expect(view.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })

  test('nullable allows Apply with no date staged', async () => {
    const view = renderPicker(null, { nullable: true })
    await openCalendar(view)
    expect(view.getByRole('button', { name: 'Apply' })).toBeEnabled()
  })

  test('timeZone is calendar context only — the committed CalendarDate is not shifted', async () => {
    const view = renderPicker(null, { nullable: true, timeZone: TZ_TOKYO })
    await openCalendar(view)
    await clickDay(view, '15')
    await apply(view)
    // A CalendarDate carries no zone; the picker's timeZone only drives the calendar context.
    expect(lastValue(view.updates)!.toString()).toBe('2026-06-15')
  })
})

describe('CmkDatePicker — save mode applies from the trigger', () => {
  // Pressing Enter in the trigger must behave exactly like clicking "Save & apply": run the save
  // handler first, and only commit + close when it succeeds.
  const tickSave = (view: PickerView) => fireEvent.click(view.getByRole('checkbox'))
  const pressEnterInTrigger = async (view: PickerView) => {
    await fireEvent.keyDown(view.getByRole('spinbutton', { name: 'Day' }), { key: 'Enter' })
    await nextTick()
  }

  test('Enter in the trigger runs the save handler, then commits and closes', async () => {
    const saveHandler = vi.fn(() => true)
    const view = renderPicker(null, { nullable: true, saveMode: true, saveHandler })
    await openCalendar(view)
    await clickDay(view, '15')
    await tickSave(view)
    await pressEnterInTrigger(view)

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(lastValue(view.updates)!.toString()).toBe('2026-06-15')
    expect(view.currentOpen()).toBe(false)
  })

  test('a rejecting save handler keeps the flyout open and commits nothing', async () => {
    const saveHandler = vi.fn(() => false)
    const view = renderPicker(null, { nullable: true, saveMode: true, saveHandler })
    await openCalendar(view)
    await clickDay(view, '15')
    await tickSave(view)
    await pressEnterInTrigger(view)

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(view.updates).toEqual([])
    expect(view.currentOpen()).toBe(true)
  })

  test('an invalid (empty, non-nullable) value never reaches the save handler', async () => {
    const saveHandler = vi.fn(() => true)
    const view = renderPicker(null, { nullable: false, saveMode: true, saveHandler })
    await openCalendar(view)
    await tickSave(view)
    await pressEnterInTrigger(view)

    expect(saveHandler).not.toHaveBeenCalled()
    expect(view.updates).toEqual([])
    expect(view.currentOpen()).toBe(true)
  })

  test('announces "Saving…" while the handler runs, then clears on success', async () => {
    let resolveHandler: (ok: boolean) => void = () => {}
    const saveHandler = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          resolveHandler = resolve
        })
    )
    const view = renderPicker(null, { nullable: true, saveMode: true, saveHandler })
    await openCalendar(view)
    await clickDay(view, '15')
    await tickSave(view)

    await fireEvent.click(view.getByRole('button', { name: 'Save & apply' }))
    await nextTick()

    // In flight: announced, still open, nothing committed yet.
    expect(view.getByText('Saving…')).toBeInTheDocument()
    expect(view.currentOpen()).toBe(true)
    expect(view.updates).toEqual([])

    resolveHandler(true)

    // Settled: announcement cleared, value committed and flyout closed.
    await waitFor(() => expect(view.currentOpen()).toBe(false))
    expect(view.queryByText('Saving…')).not.toBeInTheDocument()
    expect(lastValue(view.updates)!.toString()).toBe('2026-06-15')
  })
})
