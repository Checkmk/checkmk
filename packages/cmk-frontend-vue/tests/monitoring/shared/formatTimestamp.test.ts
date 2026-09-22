/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { formatDisplayTimestamp, formatTimestamp } from '@/monitoring/shared/formatTimestamp'
import type { DisplayOptions } from '@/monitoring/shared/types'

// Built from local components, so the expectation holds regardless of the
// machine's timezone.
function unixAt(
  year: number,
  month: number,
  day: number,
  hours: number,
  minutes: number,
  seconds: number
): number {
  return new Date(year, month, day, hours, minutes, seconds).getTime() / 1000
}

test('formats a timestamp as YYYY-MM-DD HH:MM:SS in the local timezone', () => {
  expect(formatTimestamp(unixAt(2026, 0, 5, 9, 3, 7))).toBe('2026-01-05 09:03:07')
})

test('pads single-digit date and time components', () => {
  expect(formatTimestamp(unixAt(2026, 8, 1, 0, 0, 5))).toBe('2026-09-01 00:00:05')
})

describe('formatDisplayTimestamp', () => {
  const NOW = unixAt(2026, 8, 22, 12, 0, 0)

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW * 1000)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  test('epoch renders the raw unix timestamp regardless of date format', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'epoch' }

    expect(formatDisplayTimestamp(unixAt(2026, 0, 5, 9, 3, 7), options)).toBe(
      String(Math.trunc(unixAt(2026, 0, 5, 9, 3, 7)))
    )
  })

  test.each([
    ['%Y-%m-%d', '2026-01-05 09:03:07'],
    ['%d.%m.%Y', '05.01.2026 09:03:07'],
    ['%m/%d/%Y', '01/05/2026 09:03:07'],
    ['%d.%m.', '05.01. 09:03:07'],
    ['%m/%d', '01/05 09:03:07']
  ] as const)('abs renders %s as %s', (dateFormat, expected) => {
    const options: DisplayOptions = { dateFormat, timestampFormat: 'abs' }

    expect(formatDisplayTimestamp(unixAt(2026, 0, 5, 9, 3, 7), options)).toBe(expected)
  })

  test('rel renders a recent past timestamp as an approximate age', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'rel' }

    expect(formatDisplayTimestamp(NOW - 300, options)).toBe('5 m')
  })

  test('rel renders a sub-second age in milliseconds, like the legacy renderer', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'rel' }

    expect(formatDisplayTimestamp(NOW - 0.35, options)).toBe('350 ms')
  })

  test('rel renders a future timestamp prefixed with "in"', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'rel' }

    expect(formatDisplayTimestamp(NOW + 300, options)).toBe('in 5 m')
  })

  test('mixed renders a relative age under 48 hours', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'mixed' }

    expect(formatDisplayTimestamp(NOW - 7 * 3600, options)).toBe('7 h')
  })

  test('mixed falls back to the absolute date at 48 hours and beyond', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'mixed' }
    const twoDaysAgo = NOW - 48 * 3600

    expect(formatDisplayTimestamp(twoDaysAgo, options)).toBe(formatTimestamp(twoDaysAgo))
  })

  test('both joins the absolute date and the relative age', () => {
    const options: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'both' }
    const sevenHoursAgo = NOW - 7 * 3600

    expect(formatDisplayTimestamp(sevenHoursAgo, options)).toBe(
      `${formatTimestamp(sevenHoursAgo)} - 7 h`
    )
  })
})
