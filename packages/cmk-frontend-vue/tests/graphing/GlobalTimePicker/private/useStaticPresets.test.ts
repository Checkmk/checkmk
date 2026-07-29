/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { endOfWeek, getLocalTimeZone, now, startOfWeek } from '@internationalized/date'
import type { RangePreset, Weekday } from 'cmk-ui-library/components/date-time'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { useStaticPresets } from '@/graphing/GlobalTimePicker/private/useStaticPresets'

// A Wednesday, so every week-start preference yields a distinct boundary.
const WEDNESDAY = new Date(2026, 6, 22, 15, 0, 0)

function preset(presets: RangePreset[], id: string): RangePreset {
  const found = presets.find((entry) => entry.id === id)
  expect(found).toBeDefined()
  return found!
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(WEDNESDAY)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useStaticPresets', () => {
  test('"This week" follows the browser locale without a preference', () => {
    const { from, to } = preset(useStaticPresets(), 'this-week').getRange()

    const browserLocale = new Intl.DateTimeFormat().resolvedOptions().locale
    const at = now(getLocalTimeZone())
    expect(from.toDate().getDay()).toBe(startOfWeek(at, browserLocale).toDate().getDay())
    expect(to.toDate().getDay()).toBe(endOfWeek(at, browserLocale).toDate().getDay())
  })

  test.each([
    { weekday: 1 as Weekday, fromDay: 20, toDay: 26 }, // Monday .. Sunday
    { weekday: 6 as Weekday, fromDay: 18, toDay: 24 }, // Saturday .. Friday
    { weekday: 0 as Weekday, fromDay: 19, toDay: 25 } // Sunday .. Saturday
  ])('"This week" starts on weekday $weekday when preferred', ({ weekday, fromDay, toDay }) => {
    const { from, to } = preset(
      useStaticPresets(() => weekday),
      'this-week'
    ).getRange()

    expect(from.toDate().getDay()).toBe(weekday)
    expect([from.day, from.hour, from.minute]).toEqual([fromDay, 0, 0])
    expect([to.day, to.hour, to.minute, to.second]).toEqual([toDay, 23, 59, 59])
  })

  test('the preference is resolved lazily at selection time', () => {
    let weekday: Weekday | undefined = undefined
    const presets = useStaticPresets(() => weekday)

    weekday = 1
    expect(preset(presets, 'this-week').getRange().from.toDate().getDay()).toBe(1)
  })

  test('the other presets ignore the preference', () => {
    const withPreference = preset(
      useStaticPresets(() => 1),
      'today'
    ).getRange()
    const withoutPreference = preset(useStaticPresets(), 'today').getRange()

    expect(withPreference.from.toString()).toBe(withoutPreference.from.toString())
    expect(withPreference.to.toString()).toBe(withoutPreference.to.toString())
  })
})
