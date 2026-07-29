/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  firstDayOfWeekAsWeekday,
  weekdayAsDayToken
} from '@/graphing/GlobalTimePicker/private/firstDayOfWeek'

describe('firstDayOfWeekAsWeekday', () => {
  test.each([
    { preference: 'saturday' as const, weekday: 6 },
    { preference: 'sunday' as const, weekday: 0 },
    { preference: 'monday' as const, weekday: 1 }
  ])('maps $preference to $weekday', ({ preference, weekday }) => {
    expect(firstDayOfWeekAsWeekday(preference)).toBe(weekday)
  })

  test('maps null (browser locale) to undefined', () => {
    expect(firstDayOfWeekAsWeekday(null)).toBeUndefined()
  })
})

describe('weekdayAsDayToken', () => {
  test.each([
    { weekday: 0 as const, token: 'sun' },
    { weekday: 1 as const, token: 'mon' },
    { weekday: 6 as const, token: 'sat' }
  ])('maps $weekday to $token', ({ weekday, token }) => {
    expect(weekdayAsDayToken(weekday)).toBe(token)
  })

  test('maps undefined to undefined', () => {
    expect(weekdayAsDayToken(undefined)).toBeUndefined()
  })
})
