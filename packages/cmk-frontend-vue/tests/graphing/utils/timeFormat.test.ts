/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromAbsolute } from '@internationalized/date'

import { isoDate, pad2, shortWeekday, stepLabel } from '@/graphing/utils/timeFormat'

// 2026-06-15 00:00:00 UTC
const JUNE_15_MIDNIGHT_UTC = 1781481600

describe('pad2', () => {
  test('pads a single-digit number with a leading zero', () => {
    expect(pad2(5)).toBe('05')
  })

  test('leaves a two-digit number unchanged', () => {
    expect(pad2(12)).toBe('12')
  })

  test('pads zero to two digits', () => {
    expect(pad2(0)).toBe('00')
  })
})

describe('isoDate', () => {
  test('formats a ZonedDateTime as YYYY-MM-DD', () => {
    expect(isoDate(fromAbsolute(JUNE_15_MIDNIGHT_UTC * 1000, 'UTC'))).toBe('2026-06-15')
  })

  test('pads single-digit months and days', () => {
    // 2026-01-05 00:00:00 UTC
    expect(isoDate(fromAbsolute(1767571200 * 1000, 'UTC'))).toBe('2026-01-05')
  })

  test('is timezone-aware: same instant gives a different date across midnight', () => {
    // 2026-06-14 23:00:00 UTC is still Jun 14 in UTC
    // but already Jun 15 in Europe/Berlin (CEST = UTC+2)
    const unix = (JUNE_15_MIDNIGHT_UTC - 3600) * 1000
    expect(isoDate(fromAbsolute(unix, 'UTC'))).toBe('2026-06-14')
    expect(isoDate(fromAbsolute(unix, 'Europe/Berlin'))).toBe('2026-06-15')
  })
})

describe('stepLabel', () => {
  test('formats integer minute steps below 1h', () => {
    expect(stepLabel(60)).toBe('1 m')
    expect(stepLabel(300)).toBe('5 m')
  })

  test('formats a fractional minute step with one decimal place', () => {
    expect(stepLabel(90)).toBe('1.5 m')
  })

  test('formats the 1h boundary and integer hour steps below 1d', () => {
    expect(stepLabel(3600)).toBe('1 h')
    expect(stepLabel(7200)).toBe('2 h')
  })

  test('formats a fractional hour step with one decimal place', () => {
    expect(stepLabel(5400)).toBe('1.5 h')
  })

  test('formats the 1d boundary and integer day steps', () => {
    expect(stepLabel(86400)).toBe('1 d')
    expect(stepLabel(172800)).toBe('2 d')
  })
})

describe('shortWeekday', () => {
  test('returns a non-empty string', () => {
    expect(shortWeekday(JUNE_15_MIDNIGHT_UTC, 'UTC').length).toBeGreaterThan(0)
  })

  test('is timezone-aware: same instant can fall on different weekdays across midnight', () => {
    // 2026-06-14 23:00:00 UTC: Sunday in UTC, but Monday in Europe/Berlin (CEST = UTC+2)
    const unix = JUNE_15_MIDNIGHT_UTC - 3600
    expect(shortWeekday(unix, 'UTC')).not.toBe(shortWeekday(unix, 'Europe/Berlin'))
  })
})
