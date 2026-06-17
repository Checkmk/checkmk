/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import * as intl from '@internationalized/date'
import { afterEach, describe, expect, test, vi } from 'vitest'

import {
  defaultYearRange,
  monthFromIndex,
  monthIndex,
  navTarget,
  weekdayOf
} from '@/components/date-time/private/calendar/util'
import type { Weekday } from '@/components/date-time/types'

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, today: vi.fn(actual.today), getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('monthIndex / monthFromIndex', () => {
  test('consecutive months differ by 1', () => {
    expect(
      monthIndex(new CalendarDate(2024, 2, 1)) - monthIndex(new CalendarDate(2024, 1, 1))
    ).toBe(1)
  })
  test('crossing the year boundary still differs by 1', () => {
    expect(
      monthIndex(new CalendarDate(2025, 1, 1)) - monthIndex(new CalendarDate(2024, 12, 1))
    ).toBe(1)
  })
  test('the same month one year apart differs by 12', () => {
    expect(
      monthIndex(new CalendarDate(2025, 6, 1)) - monthIndex(new CalendarDate(2024, 6, 1))
    ).toBe(12)
  })
  test('day ignored', () => {
    expect(monthIndex(new CalendarDate(2024, 1, 1))).toBe(monthIndex(new CalendarDate(2024, 1, 31)))
  })
  test('monthFromIndex returns the first of that month', () => {
    expect(monthFromIndex(monthIndex(new CalendarDate(2024, 3, 15))).toString()).toBe('2024-03-01')
  })
  test('round-trip preserves year and month', () => {
    expect(monthFromIndex(monthIndex(new CalendarDate(2024, 7, 15))).toString()).toBe('2024-07-01')
  })
})

describe('weekdayOf', () => {
  test.each([
    { date: new CalendarDate(2024, 1, 7), expected: 0 }, // Sunday
    { date: new CalendarDate(2026, 6, 10), expected: 3 } // Wednesday
  ])('$date.toString() → $expected', ({ date, expected }) => {
    expect(weekdayOf(date)).toBe(expected)
  })
})

describe('navTarget', () => {
  const from = new CalendarDate(2026, 6, 10) // a Wednesday

  test.each([
    { key: 'ArrowLeft', shift: false, fdow: 0, expected: '2026-06-09' },
    { key: 'ArrowRight', shift: false, fdow: 0, expected: '2026-06-11' },
    { key: 'ArrowUp', shift: false, fdow: 0, expected: '2026-06-03' },
    { key: 'ArrowDown', shift: false, fdow: 0, expected: '2026-06-17' },
    // firstDayOfWeek=0 → week runs Sun(07)..Sat(13).
    { key: 'Home', shift: false, fdow: 0, expected: '2026-06-07' },
    { key: 'End', shift: false, fdow: 0, expected: '2026-06-13' },
    // firstDayOfWeek=1 → week runs Mon(08)..Sun(14).
    { key: 'Home', shift: false, fdow: 1, expected: '2026-06-08' },
    { key: 'End', shift: false, fdow: 1, expected: '2026-06-14' },
    { key: 'PageUp', shift: false, fdow: 0, expected: '2026-05-10' },
    { key: 'PageDown', shift: false, fdow: 0, expected: '2026-07-10' },
    { key: 'PageUp', shift: true, fdow: 0, expected: '2025-06-10' },
    { key: 'PageDown', shift: true, fdow: 0, expected: '2027-06-10' }
  ])('$key (shift=$shift, fdow=$fdow) → $expected', ({ key, shift, fdow, expected }) => {
    expect(navTarget(key, shift, from, fdow as Weekday)!.toString()).toBe(expected)
  })

  // Month/year steps clamp the day into the target month (APG "last day if unavailable").
  test.each([
    { key: 'PageUp', shift: false, start: new CalendarDate(2026, 1, 31), expected: '2025-12-31' },
    { key: 'PageDown', shift: false, start: new CalendarDate(2026, 1, 31), expected: '2026-02-28' },
    { key: 'PageDown', shift: true, start: new CalendarDate(2024, 2, 29), expected: '2025-02-28' }
  ])('$key clamps $start.toString() → $expected', ({ key, shift, start, expected }) => {
    expect(navTarget(key, shift, start, 0 as Weekday)!.toString()).toBe(expected)
  })

  test.each(['Enter', ' ', 'Escape', 'a'])('non-navigation key %s returns null', (key) => {
    expect(navTarget(key, false, from, 0 as Weekday)).toBeNull()
  })
})

describe('defaultYearRange', () => {
  test('explicit reference', () => {
    expect(defaultYearRange(2026)).toEqual([2006, 2028])
  })
  test('explicit reference 2', () => {
    expect(defaultYearRange(2000)).toEqual([1980, 2002])
  })
  test('default arg uses today (mocked)', () => {
    vi.mocked(intl.today).mockReturnValue(new CalendarDate(2026, 6, 10))
    vi.mocked(intl.getLocalTimeZone).mockReturnValue('Europe/Berlin')
    expect(defaultYearRange()).toEqual([2006, 2028])
  })
})
