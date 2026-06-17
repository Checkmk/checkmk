/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as intl from '@internationalized/date'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { ref } from 'vue'

import type { DateTimeSettings } from '@/components/date-time/types'
import { useResolvedDateTimeSettings } from '@/components/date-time/useResolvedDateTimeSettings'

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

const mockLocale = (locale: string): void => {
  vi.spyOn(navigator, 'language', 'get').mockReturnValue(locale)
}

const mockResolvedOptions = (options: Partial<Intl.ResolvedDateTimeFormatOptions>): void => {
  vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue(
    options as Intl.ResolvedDateTimeFormatOptions
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useResolvedDateTimeSettings — hourCycle', () => {
  test('explicit 24', () => {
    expect(useResolvedDateTimeSettings(() => ({ hourCycle: 24 })).hourCycle).toBe(24)
  })
  test('explicit 12', () => {
    expect(useResolvedDateTimeSettings(() => ({ hourCycle: 12 })).hourCycle).toBe(12)
  })
  test('locale en-US', () => {
    mockLocale('en-US')
    expect(useResolvedDateTimeSettings().hourCycle).toBe(12)
  })
  test('locale de-DE', () => {
    mockLocale('de-DE')
    expect(useResolvedDateTimeSettings().hourCycle).toBe(24)
  })
  test('h11 hourCycle → 11h', () => {
    mockResolvedOptions({ hourCycle: 'h11' })
    expect(useResolvedDateTimeSettings().hourCycle).toBe(11)
  })
  test('h12 hourCycle → 12h', () => {
    mockResolvedOptions({ hourCycle: 'h12' })
    expect(useResolvedDateTimeSettings().hourCycle).toBe(12)
  })
  test('h23 hourCycle → 24h', () => {
    mockResolvedOptions({ hourCycle: 'h23' })
    expect(useResolvedDateTimeSettings().hourCycle).toBe(24)
  })
  test('absent hourCycle → 24h', () => {
    // Very old engines may not populate `hourCycle`; the fallback is 24-hour.
    mockResolvedOptions({})
    expect(useResolvedDateTimeSettings().hourCycle).toBe(24)
  })
})

describe('useResolvedDateTimeSettings — firstDayOfWeek', () => {
  test('explicit', () => {
    expect(useResolvedDateTimeSettings(() => ({ firstDayOfWeek: 1 })).firstDayOfWeek).toBe(1)
  })
  test('en-US → Sunday', () => {
    mockLocale('en-US')
    expect(useResolvedDateTimeSettings().firstDayOfWeek).toBe(0)
  })
  test('de-DE → Monday', () => {
    mockLocale('de-DE')
    expect(useResolvedDateTimeSettings().firstDayOfWeek).toBe(1)
  })
})

describe('useResolvedDateTimeSettings — dateFormat', () => {
  test('iso', () => {
    expect(useResolvedDateTimeSettings(() => ({ dateFormat: 'iso' })).dateFormat).toEqual({
      order: ['year', 'month', 'day'],
      separator: '-'
    })
  })
  test('locale en-US', () => {
    mockLocale('en-US')
    expect(useResolvedDateTimeSettings().dateFormat).toEqual({
      order: ['month', 'day', 'year'],
      separator: '/'
    })
  })
  test('locale de-DE', () => {
    mockLocale('de-DE')
    expect(useResolvedDateTimeSettings().dateFormat).toEqual({
      order: ['day', 'month', 'year'],
      separator: '.'
    })
  })
  test('fallback when <3 date parts', () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, 'formatToParts').mockReturnValue([
      { type: 'year', value: '2026' }
    ])
    expect(useResolvedDateTimeSettings().dateFormat).toEqual({
      order: ['year', 'month', 'day'],
      separator: '-'
    })
  })
})

describe('useResolvedDateTimeSettings — ICU names', () => {
  test('monthNamesShort en-US', () => {
    mockLocale('en-US')
    const { monthNamesShort } = useResolvedDateTimeSettings()
    expect(monthNamesShort).toHaveLength(12)
    expect(monthNamesShort[0]).toBe('Jan')
    expect(monthNamesShort[11]).toBe('Dec')
  })
  test('monthNamesLong en-US', () => {
    mockLocale('en-US')
    const { monthNamesLong } = useResolvedDateTimeSettings()
    expect(monthNamesLong[0]).toBe('January')
    expect(monthNamesLong[11]).toBe('December')
  })
  test('weekdayNames narrow en-US', () => {
    mockLocale('en-US')
    const { weekdayNamesNarrow } = useResolvedDateTimeSettings()
    expect(Object.keys(weekdayNamesNarrow).map(Number)).toEqual([0, 1, 2, 3, 4, 5, 6])
    expect(weekdayNamesNarrow[0]).toBe('S')
    expect(weekdayNamesNarrow[6]).toBe('S')
  })
  test('weekdayNamesShort en-US', () => {
    mockLocale('en-US')
    const { weekdayNamesShort } = useResolvedDateTimeSettings()
    expect(weekdayNamesShort[0]).toBe('Sun')
    expect(weekdayNamesShort[6]).toBe('Sat')
  })
  test('weekdayNamesLong en-US', () => {
    mockLocale('en-US')
    const { weekdayNamesLong } = useResolvedDateTimeSettings()
    expect(weekdayNamesLong[0]).toBe('Sunday')
    expect(weekdayNamesLong[6]).toBe('Saturday')
  })
})

describe('useResolvedDateTimeSettings — weekendDays & timeZone', () => {
  test('weekendDays en-US → Sat & Sun', () => {
    mockLocale('en-US')
    expect(useResolvedDateTimeSettings().weekendDays).toEqual([0, 6])
  })
  test('weekendDays de-DE → Sat & Sun', () => {
    mockLocale('de-DE')
    expect(useResolvedDateTimeSettings().weekendDays).toEqual([0, 6])
  })
  test('weekendDays ar-SA → Fri & Sat', () => {
    mockLocale('ar-SA')
    expect(useResolvedDateTimeSettings().weekendDays).toEqual([5, 6])
  })
  test('weekendDays fa-IR → Fri only', () => {
    mockLocale('fa-IR')
    expect(useResolvedDateTimeSettings().weekendDays).toEqual([5])
  })
  test('weekendDays override', () => {
    expect(useResolvedDateTimeSettings(() => ({ weekendDays: [5] })).weekendDays).toEqual([5])
  })
  test('weekendDays explicit empty is preserved', () => {
    mockLocale('en-US')
    expect(useResolvedDateTimeSettings(() => ({ weekendDays: [] })).weekendDays).toEqual([])
  })
  test('timeZone explicit', () => {
    expect(useResolvedDateTimeSettings(undefined, () => 'Asia/Tokyo').timeZone).toBe('Asia/Tokyo')
  })
  test('timeZone default', () => {
    vi.mocked(intl.getLocalTimeZone).mockReturnValue('Europe/Berlin')
    expect(useResolvedDateTimeSettings().timeZone).toBe('Europe/Berlin')
  })
})

describe('useResolvedDateTimeSettings — reactivity', () => {
  test('hourCycle recomputes', () => {
    const settings = ref<Partial<DateTimeSettings>>({ hourCycle: 12 })
    const resolved = useResolvedDateTimeSettings(settings)
    expect(resolved.hourCycle).toBe(12)
    settings.value = { hourCycle: 24 }
    expect(resolved.hourCycle).toBe(24)
  })
})
