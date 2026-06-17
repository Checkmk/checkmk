/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import * as intl from '@internationalized/date'
import { fireEvent, render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import CalendarGrid from '@/components/date-time/private/calendar/CalendarGrid.vue'
import type { CalendarSelection } from '@/components/date-time/private/calendar/types'

import { makeSettings } from '../../dateTimeTestFixtures'
import { lastValue } from '../../pickerTestHarness'

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, today: vi.fn(actual.today), getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

// Sunday-first, UTC; matches the assertions below that key off weekday 0 = Sunday.
const BASE_PROPS = {
  settings: makeSettings({ firstDayOfWeek: 0 })
}

function mountSingle(props: Record<string, unknown> = {}) {
  return render(CalendarGrid, {
    props: {
      ...BASE_PROPS,
      mode: 'single' as const,
      displayDate: new CalendarDate(2026, 6, 1),
      selection: null,
      ...props
    }
  })
}

function mountRange(props: Record<string, unknown> = {}) {
  return render(CalendarGrid, {
    props: {
      ...BASE_PROPS,
      mode: 'range' as const,
      displayDate: new CalendarDate(2026, 6, 1),
      selection: { start: null, end: null } as CalendarSelection,
      ...props
    }
  })
}

/** All 42 day gridcells in render order (each wraps an in-month <button> or is an empty placeholder). */
function dayCells(view: ReturnType<typeof mountSingle>): HTMLElement[] {
  return Array.from(view.container.querySelectorAll<HTMLElement>('[role="gridcell"]'))
}

/** The `data-date` of a gridcell's day, or null for an out-of-month placeholder. */
function cellDate(cell: HTMLElement): string | null {
  return cell.querySelector('[data-date]')?.getAttribute('data-date') ?? null
}

/** The interactive in-month button for a date, or null if that day is not in the displayed month. */
function dayButton(view: ReturnType<typeof mountSingle>, date: CalendarDate): HTMLElement | null {
  return view.container.querySelector<HTMLElement>(`[data-date="${date.toString()}"]`)
}

/** The gridcell wrapping a date's button (carries aria-selected / aria-current), or null. */
function dayGridcell(view: ReturnType<typeof mountSingle>, date: CalendarDate): HTMLElement | null {
  return dayButton(view, date)?.closest<HTMLElement>('[role="gridcell"]') ?? null
}

function lastEmittedDate(
  view: ReturnType<typeof mountSingle>,
  event: 'select' | 'update:focusedDate'
): string {
  const emitted = view.emitted(event) as Array<[CalendarDate]> | undefined
  return lastValue(emitted ?? [], event)[0].toString()
}

beforeEach(() => {
  vi.spyOn(navigator, 'language', 'get').mockReturnValue('en-US')
  // A "today" far away from the dates under test so it never collides accidentally.
  vi.mocked(intl.today).mockReturnValue(new CalendarDate(2000, 1, 1))
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CalendarGrid', () => {
  test.each([
    { name: 'June 2026', displayDate: new CalendarDate(2026, 6, 1) },
    { name: 'leap Feb 2024', displayDate: new CalendarDate(2024, 2, 1) },
    { name: 'non-leap Feb 2023', displayDate: new CalendarDate(2023, 2, 1) }
  ])('42 cells always ($name)', ({ displayDate }) => {
    expect(dayCells(mountSingle({ displayDate }))).toHaveLength(42)
  })

  test('exposes a valid ARIA grid: a header row plus 6 week rows of 7 cells', () => {
    const rows = mountSingle().container.querySelectorAll<HTMLElement>('[role="row"]')
    expect(rows).toHaveLength(7)
    // The header row holds the 7 weekday columnheaders…
    expect(rows[0]!.querySelectorAll('[role="columnheader"]')).toHaveLength(7)
    // …and each of the 6 week rows holds 7 day gridcells.
    for (const week of Array.from(rows).slice(1)) {
      expect(week.querySelectorAll('[role="gridcell"]')).toHaveLength(7)
    }
  })

  test('leadingOffset 0 when 1st == firstDayOfWeek', () => {
    // 2026-02-01 is a Sunday; with firstDayOfWeek=0 (Sunday) there are no leading days, so the
    // very first rendered cell is the 1st of the month.
    const wrapper = mountSingle({ displayDate: new CalendarDate(2026, 2, 1) })
    const first = dayCells(wrapper)[0]!
    expect(cellDate(first)).toBe('2026-02-01')
  })

  test('trailing days non-leap Feb flagged out-of-month', () => {
    const wrapper = mountSingle({ displayDate: new CalendarDate(2023, 2, 1) })
    // Feb 2023 has 28 days; day 28 is an interactive in-month button, March 1 is not.
    expect(dayButton(wrapper, new CalendarDate(2023, 2, 28))).not.toBeNull()
    expect(dayButton(wrapper, new CalendarDate(2023, 3, 1))).toBeNull()
  })

  test('leap Feb 29 in-month', () => {
    const wrapper = mountSingle({ displayDate: new CalendarDate(2024, 2, 1) })
    expect(dayButton(wrapper, new CalendarDate(2024, 2, 29))).not.toBeNull()
  })

  test('isToday exactly one', () => {
    vi.mocked(intl.today).mockReturnValue(new CalendarDate(2026, 6, 10))
    const view = mountSingle({ displayDate: new CalendarDate(2026, 6, 1) })
    const todayButtons = Array.from(
      view.container.querySelectorAll<HTMLElement>('.cmk-calendar-grid__day--today')
    )
    expect(todayButtons).toHaveLength(1)
    expect(todayButtons[0]).toHaveAttribute('data-date', '2026-06-10')
    // aria-current marks the surrounding gridcell.
    expect(dayGridcell(view, new CalendarDate(2026, 6, 10))).toHaveAttribute('aria-current', 'date')
  })

  test('dayOfWeek via tz', () => {
    // 2024-01-07 is a Sunday → weekday 0; with firstDayOfWeek=0 it sits in the first column.
    const wrapper = mountSingle({ displayDate: new CalendarDate(2024, 1, 1) })
    const idx = dayCells(wrapper).findIndex((el) => cellDate(el) === '2024-01-07')
    expect(idx % 7).toBe(0)
  })

  test('rangeBounds hover as tentative end', () => {
    const wrapper = mountRange({
      selection: { start: new CalendarDate(2026, 6, 10), end: null },
      hoverPreview: new CalendarDate(2026, 6, 15)
    })
    expect(dayGridcell(wrapper, new CalendarDate(2026, 6, 10))!.getAttribute('aria-selected')).toBe(
      'true'
    )
    expect(dayGridcell(wrapper, new CalendarDate(2026, 6, 15))!.getAttribute('aria-selected')).toBe(
      'true'
    )
    expect(
      dayButton(wrapper, new CalendarDate(2026, 6, 12))!.classList.contains(
        'cmk-calendar-grid__day--in-range'
      )
    ).toBe(true)
  })

  test('rangeBounds start==end', () => {
    const x = new CalendarDate(2026, 6, 10)
    const view = mountRange({ selection: { start: x, end: x } })
    expect(dayGridcell(view, x)!.getAttribute('aria-selected')).toBe('true')
    expect(view.container.querySelectorAll('.cmk-calendar-grid__day--in-range')).toHaveLength(0)
  })

  test('rangeBounds hover before start swaps', () => {
    const wrapper = mountRange({
      selection: { start: new CalendarDate(2026, 6, 15), end: null },
      hoverPreview: new CalendarDate(2026, 6, 10)
    })
    expect(dayGridcell(wrapper, new CalendarDate(2026, 6, 10))!.getAttribute('aria-selected')).toBe(
      'true'
    )
    expect(dayGridcell(wrapper, new CalendarDate(2026, 6, 15))!.getAttribute('aria-selected')).toBe(
      'true'
    )
    expect(
      dayButton(wrapper, new CalendarDate(2026, 6, 12))!.classList.contains(
        'cmk-calendar-grid__day--in-range'
      )
    ).toBe(true)
  })

  test('in-range strictly between, endpoints selected', () => {
    const wrapper = mountRange({
      selection: { start: new CalendarDate(2026, 6, 10), end: new CalendarDate(2026, 6, 15) }
    })
    for (const day of [11, 12, 13, 14]) {
      expect(
        dayButton(wrapper, new CalendarDate(2026, 6, day))!.classList.contains(
          'cmk-calendar-grid__day--in-range'
        )
      ).toBe(true)
    }
    const start = dayButton(wrapper, new CalendarDate(2026, 6, 10))!
    const end = dayButton(wrapper, new CalendarDate(2026, 6, 15))!
    expect(dayGridcell(wrapper, new CalendarDate(2026, 6, 10))!.getAttribute('aria-selected')).toBe(
      'true'
    )
    expect(dayGridcell(wrapper, new CalendarDate(2026, 6, 15))!.getAttribute('aria-selected')).toBe(
      'true'
    )
    expect(start.classList.contains('cmk-calendar-grid__day--in-range')).toBe(false)
    expect(end.classList.contains('cmk-calendar-grid__day--in-range')).toBe(false)
  })

  test('single-day range no in-range', () => {
    const x = new CalendarDate(2026, 6, 10)
    const view = mountRange({ selection: { start: x, end: x } })
    const selected = Array.from(
      view.container.querySelectorAll<HTMLElement>('.cmk-calendar-grid__day--selected')
    )
    expect(selected).toHaveLength(1)
    expect(selected[0]).toHaveAttribute('data-date', '2026-06-10')
    expect(view.container.querySelectorAll('.cmk-calendar-grid__day--in-range')).toHaveLength(0)
  })

  // 2026-06-10 is a Wednesday; with firstDayOfWeek=0 (Sunday) its week runs 2026-06-07..13.
  test.each([
    { key: 'ArrowLeft', shift: false, expected: '2026-06-09' },
    { key: 'ArrowRight', shift: false, expected: '2026-06-11' },
    { key: 'ArrowUp', shift: false, expected: '2026-06-03' },
    { key: 'ArrowDown', shift: false, expected: '2026-06-17' },
    { key: 'Home', shift: false, expected: '2026-06-07' },
    { key: 'End', shift: false, expected: '2026-06-13' },
    { key: 'PageUp', shift: false, expected: '2026-05-10' },
    { key: 'PageDown', shift: false, expected: '2026-07-10' },
    { key: 'PageUp', shift: true, expected: '2025-06-10' },
    { key: 'PageDown', shift: true, expected: '2027-06-10' }
  ])('navTarget $key (shift=$shift) emits $expected', async ({ key, shift, expected }) => {
    const focusedDate = new CalendarDate(2026, 6, 10)
    const view = mountSingle({ focusedDate })
    await fireEvent.keyDown(dayButton(view, focusedDate)!, { key, shiftKey: shift })
    expect(lastEmittedDate(view, 'update:focusedDate')).toBe(expected)
  })

  // Page steps clamp the day into the target month (APG "last day if unavailable").
  test.each([
    { key: 'PageUp', expected: '2025-12-31' },
    { key: 'PageDown', expected: '2026-02-28' }
  ])('navTarget $key clamps Jan 31 → $expected', async ({ key, expected }) => {
    const focusedDate = new CalendarDate(2026, 1, 31)
    const view = mountSingle({ displayDate: new CalendarDate(2026, 1, 1), focusedDate })
    await fireEvent.keyDown(dayButton(view, focusedDate)!, { key })
    expect(lastEmittedDate(view, 'update:focusedDate')).toBe(expected)
  })

  test('grid is named by its displayed month and year', () => {
    const grid = mountSingle({ displayDate: new CalendarDate(2026, 6, 1) }).container.querySelector(
      '[role="grid"]'
    )
    expect(grid).toHaveAttribute('aria-label', 'June 2026')
  })

  test('column headers expose full weekday names while showing the narrow form', () => {
    const headers = Array.from(
      mountSingle().container.querySelectorAll<HTMLElement>('[role="columnheader"]')
    )
    // firstDayOfWeek=0 → Sunday first.
    expect(headers[0]).toHaveAttribute('aria-label', 'Sunday')
    expect(headers.map((h) => h.textContent?.trim())).toEqual(['S', 'M', 'T', 'W', 'T', 'F', 'S'])
  })

  test('day button shows the number but is named by its full date (weekday omitted)', () => {
    const button = dayButton(mountSingle(), new CalendarDate(2026, 6, 10))!
    expect(button.textContent?.trim()).toBe('10')
    // The column header already conveys the weekday, so the cell label omits it.
    expect(button).toHaveAttribute('aria-label', 'June 10, 2026')
  })

  test('range endpoints announce their role in the cell label', () => {
    const view = mountRange({
      selection: { start: new CalendarDate(2026, 6, 10), end: new CalendarDate(2026, 6, 12) }
    })
    expect(dayButton(view, new CalendarDate(2026, 6, 10))!).toHaveAttribute(
      'aria-label',
      'June 10, 2026, range start'
    )
    expect(dayButton(view, new CalendarDate(2026, 6, 12))!).toHaveAttribute(
      'aria-label',
      'June 12, 2026, range end'
    )
    // An in-range day in between carries no range-role suffix.
    expect(dayButton(view, new CalendarDate(2026, 6, 11))!).toHaveAttribute(
      'aria-label',
      'June 11, 2026'
    )
  })

  test('onDayKey Enter selects and prevents default', async () => {
    const view = mountSingle({ focusedDate: new CalendarDate(2026, 6, 10) })
    const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true })
    const preventDefault = vi.spyOn(event, 'preventDefault')
    dayButton(view, new CalendarDate(2026, 6, 10))!.dispatchEvent(event)
    await nextTick()
    expect(preventDefault).toHaveBeenCalled()
    expect(lastEmittedDate(view, 'select')).toBe('2026-06-10')
  })

  test('onDayKey Space selects', async () => {
    const view = mountSingle({ focusedDate: new CalendarDate(2026, 6, 10) })
    await fireEvent.keyDown(dayButton(view, new CalendarDate(2026, 6, 10))!, { key: ' ' })
    expect(lastEmittedDate(view, 'select')).toBe('2026-06-10')
  })
})
