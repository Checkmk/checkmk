/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getLocalTimeZone } from '@internationalized/date'
import { formatDateOrRelativeDay } from 'cmk-ui-library/components/date-time/formatDateOrRelativeDay'
import type { ResolvedDateTimeSettings } from 'cmk-ui-library/components/date-time/types'

const NOW = new Date(2026, 9, 7, 15, 0)

const SETTINGS: Pick<ResolvedDateTimeSettings, 'timeZone' | 'hourCycle' | 'dateFormat'> = {
  timeZone: getLocalTimeZone(),
  hourCycle: 24,
  dateFormat: { order: ['year', 'month', 'day'], separator: '-' }
}

test('shows the time for today', () => {
  expect(formatDateOrRelativeDay(new Date(2026, 9, 7, 0, 0), SETTINGS, NOW)).toBe('00:00')
})

test('shows the time in the given hour cycle', () => {
  expect(
    formatDateOrRelativeDay(new Date(2026, 9, 7, 13, 14), { ...SETTINGS, hourCycle: 12 }, NOW)
  ).toBe('01:14 PM')
})

test('shows "Yesterday" for the whole previous day', () => {
  expect(formatDateOrRelativeDay(new Date(2026, 9, 6, 0, 0), SETTINGS, NOW)).toBe('Yesterday')
  expect(formatDateOrRelativeDay(new Date(2026, 9, 6, 23, 59), SETTINGS, NOW)).toBe('Yesterday')
})

test('shows the date before yesterday', () => {
  expect(formatDateOrRelativeDay(new Date(2026, 9, 5, 23, 59), SETTINGS, NOW)).toBe('2026-10-05')
})

test('shows the date in the given format', () => {
  expect(
    formatDateOrRelativeDay(
      new Date(2026, 0, 5),
      { ...SETTINGS, dateFormat: { order: ['day', 'month', 'year'], separator: '.' } },
      NOW
    )
  ).toBe('05.01.2026')
})

test('finds yesterday across a year boundary', () => {
  expect(
    formatDateOrRelativeDay(new Date(2025, 11, 31, 23, 59), SETTINGS, new Date(2026, 0, 1, 0, 1))
  ).toBe('Yesterday')
})

test('uses the current time by default', () => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
  onTestFinished(() => {
    vi.useRealTimers()
  })

  expect(formatDateOrRelativeDay(new Date(2026, 9, 7, 13, 14), SETTINGS)).toBe('13:14')
})
