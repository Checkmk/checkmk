/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { renderDate, renderDateAndTime, renderTimeOfDay } from 'cmk-ui-library/lib/renderTime'

// 2025-02-23T17:47:59Z
const UNIX = 1740332879

describe('renderDateAndTime', () => {
  test.each([
    { name: 'UTC', timeZone: 'UTC', expected: '2025-02-23 17:47:59' },
    { name: 'winter time in Berlin', timeZone: 'Europe/Berlin', expected: '2025-02-23 18:47:59' },
    { name: 'day shift in Tokyo', timeZone: 'Asia/Tokyo', expected: '2025-02-24 02:47:59' }
  ])('$name', ({ timeZone, expected }) => {
    expect(renderDateAndTime(UNIX, timeZone)).toBe(expected)
  })

  test('summer time in Berlin', () => {
    expect(renderDateAndTime(Date.UTC(2025, 6, 1, 10, 0, 0) / 1000, 'Europe/Berlin')).toBe(
      '2025-07-01 12:00:00'
    )
  })

  test('accepts a Date', () => {
    expect(renderDateAndTime(new Date(UNIX * 1000), 'UTC')).toBe('2025-02-23 17:47:59')
  })

  test('defaults to the browser timezone', () => {
    expect(renderDateAndTime(new Date(2026, 0, 5, 9, 3, 7))).toBe('2026-01-05 09:03:07')
  })

  test('pads single digits', () => {
    expect(renderDateAndTime(Date.UTC(2026, 0, 5, 9, 3, 7) / 1000, 'UTC')).toBe(
      '2026-01-05 09:03:07'
    )
  })
})

test('renderDate', () => {
  expect(renderDate(UNIX, 'UTC')).toBe('2025-02-23')
})

test('renderTimeOfDay', () => {
  expect(renderTimeOfDay(UNIX, 'UTC')).toBe('17:47:59')
})

test('renderTimeOfDay renders midnight as 00, not 12 AM', () => {
  expect(renderTimeOfDay(Date.UTC(2026, 0, 5) / 1000, 'UTC')).toBe('00:00:00')
})
