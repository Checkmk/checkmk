/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import * as intl from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { fireEvent, render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import DateCalendar from '@/components/date-time/private/calendar/DateCalendar.vue'
import type { CalendarSelection } from '@/components/date-time/private/calendar/types'

import { TZ_BERLIN, makeSettings } from '../../dateTimeTestFixtures'
import { lastValue, selectDropdownOption } from '../../pickerTestHarness'

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, today: vi.fn(actual.today), getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

const BASE_PROPS = {
  settings: makeSettings({ firstDayOfWeek: 0 }),
  yearRange: [2006, 2028] as [number, number]
}

function mountSingle(props: Record<string, unknown> = {}) {
  return render(DateCalendar, {
    props: { ...BASE_PROPS, mode: 'single' as const, selection: null, ...props }
  })
}

function mountRange(props: Record<string, unknown> = {}) {
  return render(DateCalendar, {
    props: {
      ...BASE_PROPS,
      mode: 'range' as const,
      selection: { start: null, end: null } as CalendarSelection,
      ...props
    }
  })
}

/** The month/year each grid currently shows, read from its first in-month day button (the 1st). */
function monthsShown(view: ReturnType<typeof mountSingle>): { month: number; year: number }[] {
  const grids = view.container.querySelectorAll('.cmk-calendar-grid')
  return Array.from(grids, (grid) => {
    const date = grid.querySelector('[data-date]')!.getAttribute('data-date')!
    const [year, month] = date.split('-').map(Number)
    return { month: month!, year: year! }
  })
}

/** Click the day button for `date` (it must be in a visible month). */
async function clickDay(view: ReturnType<typeof mountSingle>, date: CalendarDate) {
  await fireEvent.click(view.container.querySelector(`[data-date="${date.toString()}"]`)!)
  await nextTick()
}

function emittedSelection<T extends CalendarDate | CalendarSelection>(
  view: ReturnType<typeof mountSingle>
): T {
  const emitted = view.emitted('update:selection') as Array<[T]> | undefined
  return lastValue(emitted ?? [], 'update:selection')[0]
}

/** Text currently held by the polite live region that announces the displayed month/year. */
function liveRegionText(view: ReturnType<typeof mountSingle>): string {
  return view.container.querySelector('[role="status"]')!.textContent!.trim()
}

/** Press `key` on the currently focused day button. */
async function pressOnDay(view: ReturnType<typeof mountSingle>, date: CalendarDate, key: string) {
  await fireEvent.keyDown(view.container.querySelector(`[data-date="${date.toString()}"]`)!, {
    key
  })
  await nextTick()
}

beforeEach(() => {
  vi.spyOn(navigator, 'language', 'get').mockReturnValue('en-US')
  vi.mocked(intl.today).mockReturnValue(new CalendarDate(2026, 6, 10))
  vi.mocked(intl.getLocalTimeZone).mockReturnValue(TZ_BERLIN)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DateCalendar selection', () => {
  test('single select', async () => {
    const view = mountSingle()
    await clickDay(view, new CalendarDate(2026, 6, 20))
    expect(emittedSelection<CalendarDate>(view).toString()).toBe('2026-06-20')
    // focusedDate follows the selection: the selected day becomes the roving-tabindex target.
    expect(view.container.querySelector('[data-date="2026-06-20"]')).toHaveAttribute(
      'tabindex',
      '0'
    )
  })

  test('range begin (start null)', async () => {
    const view = mountRange()
    await clickDay(view, new CalendarDate(2026, 6, 10))
    const value = emittedSelection<CalendarSelection>(view)
    expect(value.start!.toString()).toBe('2026-06-10')
    expect(value.end).toBeNull()
  })

  test('range restart (end set)', async () => {
    const view = mountRange({
      selection: { start: new CalendarDate(2026, 6, 5), end: new CalendarDate(2026, 6, 8) }
    })
    await clickDay(view, new CalendarDate(2026, 6, 20))
    const value = emittedSelection<CalendarSelection>(view)
    expect(value.start!.toString()).toBe('2026-06-20')
    expect(value.end).toBeNull()
  })

  test('range end after start', async () => {
    const view = mountRange({ selection: { start: new CalendarDate(2026, 6, 5), end: null } })
    await clickDay(view, new CalendarDate(2026, 6, 20))
    const value = emittedSelection<CalendarSelection>(view)
    expect(value.start!.toString()).toBe('2026-06-05')
    expect(value.end!.toString()).toBe('2026-06-20')
  })

  test('range end before start swaps', async () => {
    const view = mountRange({ selection: { start: new CalendarDate(2026, 6, 20), end: null } })
    await clickDay(view, new CalendarDate(2026, 6, 5))
    const value = emittedSelection<CalendarSelection>(view)
    expect(value.start!.toString()).toBe('2026-06-05')
    expect(value.end!.toString()).toBe('2026-06-20')
  })

  test('range end == start', async () => {
    const day = new CalendarDate(2026, 6, 5)
    const view = mountRange({ selection: { start: day, end: null } })
    await clickDay(view, day)
    const value = emittedSelection<CalendarSelection>(view)
    expect(value.start!.toString()).toBe('2026-06-05')
    expect(value.end!.toString()).toBe('2026-06-05')
  })
})

describe('DateCalendar month/year live region', () => {
  test('announces the focused month on mount', () => {
    expect(liveRegionText(mountSingle())).toBe('June 2026')
  })

  test('updates when Page navigation changes the month', async () => {
    const view = mountSingle()
    await pressOnDay(view, new CalendarDate(2026, 6, 10), 'PageDown')
    expect(liveRegionText(view)).toBe('July 2026')
  })

  test('stays unchanged while navigating within the same month', async () => {
    const view = mountSingle()
    await pressOnDay(view, new CalendarDate(2026, 6, 10), 'ArrowRight')
    expect(liveRegionText(view)).toBe('June 2026')
  })
})

describe('DateCalendar visible window (targetBase / leftFreeGrids)', () => {
  test('targetBase single visible on update keeps window', async () => {
    // today June 2026 → initial window June. Selecting a June date keeps the window on June.
    const view = mountSingle()
    expect(monthsShown(view)[0]).toEqual({ month: 6, year: 2026 })
    await view.rerender({ selection: new CalendarDate(2026, 6, 25) })
    expect(monthsShown(view)[0]).toEqual({ month: 6, year: 2026 })
  })

  test('targetBase single offscreen re-centers on anchor', async () => {
    const view = mountSingle()
    await view.rerender({ selection: new CalendarDate(2026, 9, 15) })
    expect(monthsShown(view)[0]).toEqual({ month: 9, year: 2026 })
  })

  test('targetBase range span > grids ends in last grid', () => {
    // 2 grids, range spanning 5 months (March..July 2026). end month July (7); with 2 grids the
    // first visible month is July - 1 = June.
    const view = mountRange({
      grids: 2,
      selection: { start: new CalendarDate(2026, 3, 1), end: new CalendarDate(2026, 7, 1) }
    })
    expect(monthsShown(view)).toEqual([
      { month: 6, year: 2026 },
      { month: 7, year: 2026 }
    ])
  })

  test('leftFreeGrids even centers', async () => {
    // 3 grids, single anchor (span 1) → free=2, even → 1 free grid on the left. Anchor offscreen
    // so it re-centers: September 2026 → August first visible, September second, October third.
    const view = mountSingle({ grids: 3 })
    await view.rerender({ selection: new CalendarDate(2026, 9, 15) })
    expect(monthsShown(view)).toEqual([
      { month: 8, year: 2026 },
      { month: 9, year: 2026 },
      { month: 10, year: 2026 }
    ])
  })

  test('leftFreeGrids odd, strictly future → extra grid on left', async () => {
    // 2 grids, single anchor strictly after today June 2026: December 2026. free=1, odd, future →
    // extra grid on left → November first visible, December second.
    const view = mountSingle({ grids: 2 })
    await view.rerender({ selection: new CalendarDate(2026, 12, 15) })
    expect(monthsShown(view)).toEqual([
      { month: 11, year: 2026 },
      { month: 12, year: 2026 }
    ])
  })

  test('leftFreeGrids odd, not future → extra grid on right', async () => {
    // 2 grids, single anchor before today: March 2026 < June 2026. free=1, odd, not future →
    // no free grid on left → March first visible, April second.
    const view = mountSingle({ grids: 2 })
    await view.rerender({ selection: new CalendarDate(2026, 3, 15) })
    expect(monthsShown(view)).toEqual([
      { month: 3, year: 2026 },
      { month: 4, year: 2026 }
    ])
  })

  test('targetBase range start null on update keeps window', async () => {
    const view = mountRange()
    expect(monthsShown(view)[0]).toEqual({ month: 6, year: 2026 })
    await view.rerender({ selection: { start: null, end: null } })
    expect(monthsShown(view)[0]).toEqual({ month: 6, year: 2026 })
  })
})

describe('DateCalendar grid month/year dropdowns', () => {
  test('month dropdown sets the first grid', async () => {
    const user = userEvent.setup()
    const view = mountSingle()
    await selectDropdownOption(user, 'Month', 'May')
    expect(monthsShown(view)[0]!.month).toBe(5)
  })

  test('year dropdown on the second grid keeps the columns aligned', async () => {
    const user = userEvent.setup()
    const view = mountSingle({ grids: 2 })
    // Set grid 1 to 2020 (keeping its month July); the first column follows as June 2020.
    await selectDropdownOption(user, 'Year', '2020', 1)
    expect(monthsShown(view)).toEqual([
      { month: 6, year: 2020 },
      { month: 7, year: 2020 }
    ])
  })
})
