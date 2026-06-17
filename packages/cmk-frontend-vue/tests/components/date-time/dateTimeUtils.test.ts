/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate, CalendarDateTime, toZoned } from '@internationalized/date'
import { describe, expect, test } from 'vitest'

import {
  formatDate,
  formatTime,
  fromMeridiemHour,
  instantToParts,
  isDateTimeParts,
  isEmptyDateTimePartsDraft,
  isRangeInverted,
  partsToInstant,
  partsToZoned,
  swapRangeEndpoints,
  timeZoneRegionLabel,
  timeZoneShortLabel,
  toMeridiemHour,
  zonedToParts
} from '@/components/date-time/dateTimeUtils'
import type {
  DateFormatParts,
  DateTimePartsDraft,
  HourCycle,
  Meridiem,
  MeridiemCycle,
  RangeDraft,
  TimeValue
} from '@/components/date-time/types'

import { TZ_BERLIN, TZ_TOKYO, TZ_UTC } from './dateTimeTestFixtures'

const NOW = new Date('2026-06-10T10:00:00Z')

describe('toMeridiemHour', () => {
  test.each<{ name: string; hour: number; cycle: MeridiemCycle; expected: object }>([
    // h12: the noon/midnight slot shows as 12.
    { name: 'h12 midnight', hour: 0, cycle: 12, expected: { displayHour: 12, meridiem: 'AM' } },
    { name: 'h12 noon', hour: 12, cycle: 12, expected: { displayHour: 12, meridiem: 'PM' } },
    { name: 'h12 morning', hour: 11, cycle: 12, expected: { displayHour: 11, meridiem: 'AM' } },
    { name: 'h12 1 PM', hour: 13, cycle: 12, expected: { displayHour: 1, meridiem: 'PM' } },
    { name: 'h12 11 PM', hour: 23, cycle: 12, expected: { displayHour: 11, meridiem: 'PM' } },
    // h11: the noon/midnight slot shows as 0.
    { name: 'h11 midnight', hour: 0, cycle: 11, expected: { displayHour: 0, meridiem: 'AM' } },
    { name: 'h11 noon', hour: 12, cycle: 11, expected: { displayHour: 0, meridiem: 'PM' } },
    { name: 'h11 morning', hour: 11, cycle: 11, expected: { displayHour: 11, meridiem: 'AM' } },
    { name: 'h11 1 PM', hour: 13, cycle: 11, expected: { displayHour: 1, meridiem: 'PM' } },
    { name: 'h11 11 PM', hour: 23, cycle: 11, expected: { displayHour: 11, meridiem: 'PM' } }
  ])('$name', ({ hour, cycle, expected }) => {
    expect(toMeridiemHour(hour, cycle)).toEqual(expected)
  })
  test.each([24, -1])('throws for out-of-range hour %i', (hour) => {
    expect(() => toMeridiemHour(hour, 12)).toThrow()
  })
})

describe('fromMeridiemHour', () => {
  test.each<{ name: string; displayHour: number; meridiem: Meridiem; expected: number }>([
    { name: 'h12 12 AM → midnight', displayHour: 12, meridiem: 'AM', expected: 0 },
    { name: 'h12 12 PM → noon', displayHour: 12, meridiem: 'PM', expected: 12 },
    { name: 'h11 0 AM → midnight', displayHour: 0, meridiem: 'AM', expected: 0 },
    { name: 'h11 0 PM → noon', displayHour: 0, meridiem: 'PM', expected: 12 },
    { name: '1 AM', displayHour: 1, meridiem: 'AM', expected: 1 },
    { name: '1 PM', displayHour: 1, meridiem: 'PM', expected: 13 },
    { name: '11 PM', displayHour: 11, meridiem: 'PM', expected: 23 }
  ])('$name', ({ displayHour, meridiem, expected }) => {
    expect(fromMeridiemHour(displayHour, meridiem)).toBe(expected)
  })
  test.each([13, -1])('throws for out-of-range displayHour %i', (displayHour) => {
    expect(() => fromMeridiemHour(displayHour, 'AM')).toThrow()
  })
  test.each<MeridiemCycle>([11, 12])('round-trip for h=0..23 in h%i', (cycle) => {
    for (let hour = 0; hour <= 23; hour++) {
      const { displayHour, meridiem } = toMeridiemHour(hour, cycle)
      expect(fromMeridiemHour(displayHour, meridiem)).toBe(hour)
    }
  })
})

describe('formatDate', () => {
  test.each<{ name: string; date: CalendarDate; format: DateFormatParts; expected: string }>([
    {
      name: 'ISO',
      date: new CalendarDate(2026, 3, 9),
      format: { order: ['year', 'month', 'day'], separator: '-' },
      expected: '2026-03-09'
    },
    {
      name: 'US locale order',
      date: new CalendarDate(2026, 3, 9),
      format: { order: ['month', 'day', 'year'], separator: '/' },
      expected: '03/09/2026'
    },
    {
      name: 'DE locale order',
      date: new CalendarDate(2026, 3, 9),
      format: { order: ['day', 'month', 'year'], separator: '.' },
      expected: '09.03.2026'
    },
    {
      name: 'sub-1000 year padding',
      date: new CalendarDate(99, 3, 9),
      format: { order: ['year', 'month', 'day'], separator: '-' },
      expected: '0099-03-09'
    }
  ])('$name', ({ date, format, expected }) => {
    expect(formatDate(date, format)).toBe(expected)
  })
})

describe('formatTime', () => {
  test.each<{ name: string; time: TimeValue; hourCycle: HourCycle; expected: string }>([
    { name: '24h', time: { hour: 20, minute: 45 }, hourCycle: 24, expected: '20:45' },
    { name: '12h PM', time: { hour: 20, minute: 45 }, hourCycle: 12, expected: '08:45 PM' },
    { name: '24h midnight', time: { hour: 0, minute: 0 }, hourCycle: 24, expected: '00:00' },
    { name: '12h midnight', time: { hour: 0, minute: 0 }, hourCycle: 12, expected: '12:00 AM' },
    { name: '12h noon', time: { hour: 12, minute: 0 }, hourCycle: 12, expected: '12:00 PM' },
    { name: 'h11 midnight', time: { hour: 0, minute: 0 }, hourCycle: 11, expected: '00:00 AM' },
    { name: 'h11 noon', time: { hour: 12, minute: 0 }, hourCycle: 11, expected: '00:00 PM' },
    { name: 'h11 PM', time: { hour: 20, minute: 45 }, hourCycle: 11, expected: '08:45 PM' },
    { name: 'minute zero-pad', time: { hour: 9, minute: 5 }, hourCycle: 24, expected: '09:05' }
  ])('$name', ({ time, hourCycle, expected }) => {
    expect(formatTime(time, hourCycle)).toBe(expected)
  })
})

describe('timeZoneRegionLabel', () => {
  test.each([
    { name: 'two parts', input: 'Europe/Berlin', expected: 'Europe, Berlin' },
    {
      name: 'three parts + underscore',
      input: 'America/Argentina/Buenos_Aires',
      expected: 'America, Argentina, Buenos Aires'
    },
    { name: 'single token', input: 'UTC', expected: 'UTC' },
    { name: 'empty → Unknown Timezone', input: '', expected: 'Unknown Timezone' }
  ])('$name', ({ input, expected }) => {
    expect(timeZoneRegionLabel(input)).toBe(expected)
  })
})

describe('timeZoneShortLabel', () => {
  test.each([
    {
      name: 'standard time',
      tz: TZ_BERLIN,
      at: new Date('2024-01-15T12:00:00Z'),
      expected: 'CET (UTC+1)'
    },
    {
      name: 'DST summer time',
      tz: TZ_BERLIN,
      at: new Date('2024-07-15T12:00:00Z'),
      expected: 'CEST (UTC+2)'
    },
    { name: 'zero offset', tz: TZ_UTC, at: NOW, expected: 'UTC' },
    { name: 'no English abbreviation → offset only', tz: TZ_TOKYO, at: NOW, expected: 'UTC+9' }
  ])('$name', ({ tz, at, expected }) => {
    expect(timeZoneShortLabel(tz, at)).toBe(expected)
  })
})

describe('zonedToParts', () => {
  test('basic split', () => {
    const parts = zonedToParts(
      toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_BERLIN, 'compatible')
    )
    expect(parts.date.toString()).toBe('2026-03-09')
    expect(parts.time).toEqual({ hour: 8, minute: 45 })
  })
  test('seconds dropped', () => {
    const parts = zonedToParts(
      toZoned(new CalendarDateTime(2026, 3, 9, 8, 45, 30), TZ_BERLIN, 'compatible')
    )
    expect(parts.time).toEqual({ hour: 8, minute: 45 })
  })
  test('fall-back fold keeps wall hour', () => {
    const parts = zonedToParts(
      toZoned(new CalendarDateTime(2024, 10, 27, 2, 30), TZ_BERLIN, 'earlier')
    )
    expect(parts.date.toString()).toBe('2024-10-27')
    expect(parts.time).toEqual({ hour: 2, minute: 30 })
  })
})

describe('partsToZoned', () => {
  test('normal, no current', () => {
    const result = partsToZoned(
      new CalendarDate(2026, 3, 9),
      { hour: 8, minute: 45 },
      TZ_BERLIN,
      null
    )
    expect(result.toAbsoluteString()).toBe(
      toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_BERLIN, 'compatible').toAbsoluteString()
    )
  })
  test('spring-forward gap moves forward', () => {
    const result = partsToZoned(
      new CalendarDate(2024, 3, 31),
      { hour: 2, minute: 30 },
      TZ_BERLIN,
      null
    )
    expect(result.hour).toBe(3)
    expect(result.minute).toBe(30)
  })
  test('fall-back ambiguous → earlier offset', () => {
    const result = partsToZoned(
      new CalendarDate(2024, 10, 27),
      { hour: 2, minute: 30 },
      TZ_BERLIN,
      null
    )
    expect(result.toAbsoluteString()).toBe('2024-10-27T00:30:00.000Z')
  })
  test('no-op preserve (ordinary)', () => {
    const current = toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_BERLIN, 'compatible')
    const result = partsToZoned(
      new CalendarDate(2026, 3, 9),
      { hour: 8, minute: 45 },
      TZ_BERLIN,
      current
    )
    expect(result).toBe(current)
  })
  test('no-op preserve in fold keeps exact instant', () => {
    const current = toZoned(new CalendarDateTime(2024, 10, 27, 2, 30), TZ_BERLIN, 'later')
    const result = partsToZoned(
      new CalendarDate(2024, 10, 27),
      { hour: 2, minute: 30 },
      TZ_BERLIN,
      current
    )
    expect(result).toBe(current)
  })
  test('edited by 1 minute', () => {
    const current = toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_BERLIN, 'compatible')
    const result = partsToZoned(
      new CalendarDate(2026, 3, 9),
      { hour: 8, minute: 46 },
      TZ_BERLIN,
      current
    )
    expect(result).not.toBe(current)
    expect(result.minute).toBe(46)
  })
  test('current in other tz, same wall clock in timeZone', () => {
    // UTC 08:45 is Berlin wall 09:45 in March (UTC+1); reading it back in Berlin matches the parts.
    const current = toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_UTC, 'compatible')
    const result = partsToZoned(
      new CalendarDate(2026, 3, 9),
      { hour: 9, minute: 45 },
      TZ_BERLIN,
      current
    )
    expect(result).toBe(current)
  })
})

describe('instantToParts', () => {
  test('null passes through', () => {
    expect(instantToParts(null, TZ_BERLIN)).toEqual({ date: null, time: null })
  })
  test('reads wall clock in tz', () => {
    const value = toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_UTC, 'compatible')
    const parts = instantToParts(value, TZ_BERLIN)
    expect(parts.date?.toString()).toBe('2026-03-09')
    expect(parts.time).toEqual({ hour: 9, minute: 45 })
  })
})

describe('date-time draft helpers', () => {
  test.each<{ name: string; value: DateTimePartsDraft; expected: boolean }>([
    {
      name: 'complete draft',
      value: { date: new CalendarDate(2026, 3, 9), time: { hour: 8, minute: 45 } },
      expected: true
    },
    {
      name: 'missing date',
      value: { date: null, time: { hour: 8, minute: 45 } },
      expected: false
    },
    {
      name: 'missing time',
      value: { date: new CalendarDate(2026, 3, 9), time: null },
      expected: false
    }
  ])('isDateTimeParts — $name', ({ value, expected }) => {
    expect(isDateTimeParts(value)).toBe(expected)
  })

  test.each<{ name: string; value: DateTimePartsDraft; expected: boolean }>([
    { name: 'fully empty', value: { date: null, time: null }, expected: true },
    {
      name: 'date only',
      value: { date: new CalendarDate(2026, 3, 9), time: null },
      expected: false
    },
    {
      name: 'time only',
      value: { date: null, time: { hour: 8, minute: 45 } },
      expected: false
    }
  ])('isEmptyDateTimePartsDraft — $name', ({ value, expected }) => {
    expect(isEmptyDateTimePartsDraft(value)).toBe(expected)
  })
})

describe('partsToInstant', () => {
  test('complete parts compose an instant', () => {
    const result = partsToInstant(
      { date: new CalendarDate(2026, 3, 9), time: { hour: 8, minute: 45 } },
      TZ_BERLIN,
      null
    )
    expect(result.toAbsoluteString()).toBe(
      toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_BERLIN, 'compatible').toAbsoluteString()
    )
  })
  test('unchanged parts preserve', () => {
    const current = toZoned(new CalendarDateTime(2026, 3, 9, 8, 45), TZ_BERLIN, 'compatible')
    const result = partsToInstant(
      { date: new CalendarDate(2026, 3, 9), time: { hour: 8, minute: 45 } },
      TZ_BERLIN,
      current
    )
    expect(result).toBe(current)
  })
})

describe('isRangeInverted', () => {
  test.each<{ name: string; draft: RangeDraft; expected: boolean }>([
    {
      name: 'ordered (same day, by time)',
      draft: {
        from: { date: new CalendarDate(2026, 3, 9), time: { hour: 10, minute: 0 } },
        to: { date: new CalendarDate(2026, 3, 9), time: { hour: 12, minute: 0 } }
      },
      expected: false
    },
    {
      name: 'inverted (same day, by time)',
      draft: {
        from: { date: new CalendarDate(2026, 3, 9), time: { hour: 14, minute: 0 } },
        to: { date: new CalendarDate(2026, 3, 9), time: { hour: 12, minute: 0 } }
      },
      expected: true
    },
    {
      name: 'inverted by date (time ordered)',
      draft: {
        from: { date: new CalendarDate(2026, 3, 10), time: { hour: 8, minute: 0 } },
        to: { date: new CalendarDate(2026, 3, 9), time: { hour: 20, minute: 0 } }
      },
      expected: true
    },
    {
      name: 'equal wall-clock ⇒ not inverted',
      draft: {
        from: { date: new CalendarDate(2026, 3, 9), time: { hour: 12, minute: 0 } },
        to: { date: new CalendarDate(2026, 3, 9), time: { hour: 12, minute: 0 } }
      },
      expected: false
    },
    {
      name: 'incomplete (from.time null) ⇒ false',
      draft: {
        from: { date: new CalendarDate(2026, 3, 9), time: null },
        to: { date: new CalendarDate(2026, 3, 9), time: { hour: 0, minute: 0 } }
      },
      expected: false
    },
    {
      name: 'incomplete (to.time null) ⇒ false',
      draft: {
        from: { date: new CalendarDate(2026, 3, 9), time: { hour: 23, minute: 59 } },
        to: { date: new CalendarDate(2026, 3, 9), time: null }
      },
      expected: false
    },
    {
      name: 'incomplete (from.date null) ⇒ false',
      draft: {
        from: { date: null, time: { hour: 10, minute: 0 } },
        to: { date: new CalendarDate(2026, 3, 9), time: { hour: 12, minute: 0 } }
      },
      expected: false
    },
    {
      name: 'incomplete (to.date null) ⇒ false',
      draft: {
        from: { date: new CalendarDate(2026, 3, 9), time: { hour: 12, minute: 0 } },
        to: { date: null, time: { hour: 10, minute: 0 } }
      },
      expected: false
    }
  ])('$name', ({ draft, expected }) => {
    expect(isRangeInverted(draft)).toBe(expected)
  })
})

describe('swapRangeEndpoints', () => {
  test('exchanges endpoints', () => {
    const a = new CalendarDate(2026, 3, 9)
    const b = new CalendarDate(2026, 4, 1)
    const draft: RangeDraft = {
      from: { date: a, time: { hour: 8, minute: 0 } },
      to: { date: b, time: { hour: 9, minute: 30 } }
    }
    expect(swapRangeEndpoints(draft)).toEqual({
      from: { date: b, time: { hour: 9, minute: 30 } },
      to: { date: a, time: { hour: 8, minute: 0 } }
    })
  })
  test('involutive', () => {
    const draft: RangeDraft = {
      from: { date: new CalendarDate(2026, 3, 9), time: { hour: 8, minute: 0 } },
      to: { date: new CalendarDate(2026, 4, 1), time: { hour: 9, minute: 30 } }
    }
    expect(swapRangeEndpoints(swapRangeEndpoints(draft))).toEqual(draft)
  })
  test('carries nulls', () => {
    const draft: RangeDraft = {
      from: { date: new CalendarDate(2026, 3, 9), time: null },
      to: { date: new CalendarDate(2026, 4, 1), time: { hour: 8, minute: 0 } }
    }
    const swapped = swapRangeEndpoints(draft)
    expect(swapped.from.time).toEqual({ hour: 8, minute: 0 })
    expect(swapped.to.time).toBeNull()
  })
})
