/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'
import { ref } from 'vue'

import type { SegmentText } from '@/components/date-time/private/input/useSegmentedField'
import { useTimeField } from '@/components/date-time/private/input/useTimeField'
import type { HourCycle, TimeValue } from '@/components/date-time/types'

const timeField = (hourCycle: HourCycle = 24) => useTimeField(() => hourCycle).value

describe('useTimeField.toValue', () => {
  test.each<{ name: string; hourCycle: HourCycle; text: SegmentText; expected: TimeValue | null }>([
    {
      name: '24h complete',
      hourCycle: 24,
      text: { hour: '08', minute: '05' },
      expected: { hour: 8, minute: 5 }
    },
    {
      name: '12h PM recombine',
      hourCycle: 12,
      text: { hour: '05', minute: '05', meridiem: 'PM' },
      expected: { hour: 17, minute: 5 }
    },
    {
      name: '12h no meridiem ⇒ AM',
      hourCycle: 12,
      text: { hour: '05', minute: '00' },
      expected: { hour: 5, minute: 0 }
    },
    {
      name: '12h 12 AM → 0',
      hourCycle: 12,
      text: { hour: '12', minute: '00', meridiem: 'AM' },
      expected: { hour: 0, minute: 0 }
    },
    {
      name: 'h11 0 AM → 0',
      hourCycle: 11,
      text: { hour: '00', minute: '00', meridiem: 'AM' },
      expected: { hour: 0, minute: 0 }
    },
    {
      name: 'h11 0 PM → noon',
      hourCycle: 11,
      text: { hour: '00', minute: '00', meridiem: 'PM' },
      expected: { hour: 12, minute: 0 }
    },
    { name: 'hour empty → null', hourCycle: 24, text: { hour: '', minute: '05' }, expected: null },
    { name: 'minute empty → null', hourCycle: 24, text: { hour: '08', minute: '' }, expected: null }
  ])('$name', ({ hourCycle, text, expected }) => {
    const result = timeField(hourCycle).toValue(text)
    if (expected === null) {
      expect(result).toBeNull()
    } else {
      expect(result).toEqual(expected)
    }
  })
})

describe('useTimeField.toText', () => {
  test('null keeps sticky meridiem', () => {
    expect(timeField(12).toText(null, { meridiem: 'PM' })).toEqual({
      hour: '',
      minute: '',
      meridiem: 'PM'
    })
  })
  test('null no prev → AM', () => {
    expect(timeField(12).toText(null, {})).toEqual({ hour: '', minute: '', meridiem: 'AM' })
  })
  test('24h', () => {
    expect(timeField(24).toText({ hour: 13, minute: 5 }, {})).toEqual({ hour: '13', minute: '05' })
  })
  test('12h PM', () => {
    expect(timeField(12).toText({ hour: 13, minute: 5 }, {})).toEqual({
      hour: '01',
      minute: '05',
      meridiem: 'PM'
    })
  })
  test('h11 noon → 00 PM', () => {
    expect(timeField(11).toText({ hour: 12, minute: 5 }, {})).toEqual({
      hour: '00',
      minute: '05',
      meridiem: 'PM'
    })
  })
})

describe('useTimeField.normalize', () => {
  test.each<{ name: string; hourCycle: HourCycle; text: SegmentText; expected: SegmentText }>([
    {
      name: '24h over max clamps',
      hourCycle: 24,
      text: { hour: '25', minute: '' },
      expected: { hour: '23' }
    },
    {
      name: 'minute over max clamps',
      hourCycle: 24,
      text: { hour: '', minute: '75' },
      expected: { minute: '59' }
    },
    {
      name: '12h typed "13" pins PM',
      hourCycle: 12,
      text: { hour: '13' },
      expected: { hour: '01', meridiem: 'PM' }
    },
    {
      name: '12h typed "00" → 12 AM',
      hourCycle: 12,
      text: { hour: '00' },
      expected: { hour: '12', meridiem: 'AM' }
    },
    {
      name: '12h 1-12 keeps shown meridiem',
      hourCycle: 12,
      text: { hour: '05', meridiem: 'PM' },
      expected: { hour: '05', meridiem: 'PM' }
    },
    {
      name: 'h11 typed "12" → 0 PM',
      hourCycle: 11,
      text: { hour: '12' },
      expected: { hour: '00', meridiem: 'PM' }
    },
    {
      name: 'h11 typed "00" keeps shown meridiem',
      hourCycle: 11,
      text: { hour: '00', meridiem: 'AM' },
      expected: { hour: '00', meridiem: 'AM' }
    },
    {
      name: 'h11 typed "13" pins PM',
      hourCycle: 11,
      text: { hour: '13' },
      expected: { hour: '01', meridiem: 'PM' }
    },
    {
      name: 'empty stays empty',
      hourCycle: 24,
      text: { hour: '', minute: '' },
      expected: { hour: '', minute: '' }
    }
  ])('$name', ({ hourCycle, text, expected }) => {
    expect(timeField(hourCycle).normalize(text)).toMatchObject(expected)
  })
})

describe('useTimeField.step — hour', () => {
  test.each<{
    name: string
    hourCycle: HourCycle
    text: SegmentText
    delta: 1 | -1
    hour: string
    meridiem?: string
    carry?: 1 | -1
  }>([
    {
      name: 'null hour, 12h, sticky PM',
      hourCycle: 12,
      text: { hour: '', meridiem: 'PM' },
      delta: 1,
      hour: '01',
      meridiem: 'PM'
    },
    {
      name: 'null hour, 12h, AM',
      hourCycle: 12,
      text: { hour: '', meridiem: 'AM' },
      delta: 1,
      hour: '01',
      meridiem: 'AM'
    },
    { name: 'null hour, 24h', hourCycle: 24, text: { hour: '' }, delta: 1, hour: '00' },
    {
      name: '23 +1 carries +1 day',
      hourCycle: 24,
      text: { hour: '23' },
      delta: 1,
      hour: '00',
      carry: 1
    },
    {
      name: '00 −1 carries −1 day',
      hourCycle: 24,
      text: { hour: '00' },
      delta: -1,
      hour: '23',
      carry: -1
    },
    { name: 'mid-range no carry', hourCycle: 24, text: { hour: '12' }, delta: 1, hour: '13' },
    {
      name: '12h 11 PM +1 carries +1 day',
      hourCycle: 12,
      text: { hour: '11', meridiem: 'PM' },
      delta: 1,
      hour: '12',
      meridiem: 'AM',
      carry: 1
    },
    {
      name: 'null hour, h11, AM → 00',
      hourCycle: 11,
      text: { hour: '', meridiem: 'AM' },
      delta: 1,
      hour: '00',
      meridiem: 'AM'
    },
    {
      name: 'h11 11 PM +1 carries +1 day',
      hourCycle: 11,
      text: { hour: '11', meridiem: 'PM' },
      delta: 1,
      hour: '00',
      meridiem: 'AM',
      carry: 1
    }
  ])('$name', ({ hourCycle, text, delta, hour, meridiem, carry }) => {
    const result = timeField(hourCycle).step(text, 'hour', delta)
    expect(result.text.hour).toBe(hour)
    if (meridiem !== undefined) {
      expect(result.text.meridiem).toBe(meridiem)
    }
    expect(result.carry).toBe(carry)
  })
})

describe('useTimeField.step — minute', () => {
  test.each<{
    name: string
    text: SegmentText
    delta: 1 | -1
    minute: string
    hour?: string
    carry?: 1 | -1
  }>([
    { name: 'null minute initializes', text: { hour: '08', minute: '' }, delta: 1, minute: '00' },
    {
      name: 'null hour: dial alone wraps up',
      text: { hour: '', minute: '59' },
      delta: 1,
      minute: '00'
    },
    {
      name: 'null hour: dial alone wraps down',
      text: { hour: '', minute: '00' },
      delta: -1,
      minute: '59'
    },
    {
      name: '23:59 +1 carries +1 day',
      text: { hour: '23', minute: '59' },
      delta: 1,
      hour: '00',
      minute: '00',
      carry: 1
    },
    {
      name: '00:00 −1 carries −1 day',
      text: { hour: '00', minute: '00' },
      delta: -1,
      hour: '23',
      minute: '59',
      carry: -1
    },
    {
      name: 'hour rollover within day',
      text: { hour: '08', minute: '59' },
      delta: 1,
      hour: '09',
      minute: '00'
    }
  ])('$name', ({ text, delta, minute, hour, carry }) => {
    const result = timeField(24).step(text, 'minute', delta)
    expect(result.text.minute).toBe(minute)
    if (hour !== undefined) {
      expect(result.text.hour).toBe(hour)
    }
    expect(result.carry).toBe(carry)
  })
})

describe('useTimeField.step — meridiem', () => {
  test.each<{ name: string; text: SegmentText; expected: string }>([
    { name: 'AM → PM', text: { meridiem: 'AM' }, expected: 'PM' },
    { name: 'PM → AM', text: { meridiem: 'PM' }, expected: 'AM' },
    { name: 'default (none) toggles PM', text: {}, expected: 'PM' }
  ])('$name', ({ text, expected }) => {
    const result = timeField(12).step(text, 'meridiem', 1)
    expect(result.text.meridiem).toBe(expected)
    expect(result.carry).toBeUndefined()
  })
})

describe('useTimeField.isComplete', () => {
  test.each([
    { name: 'hour "3" auto-advances (30>23)', key: 'hour', digits: '3', expected: true },
    { name: 'hour "1" stays', key: 'hour', digits: '1', expected: false },
    { name: 'hour "2" stays', key: 'hour', digits: '2', expected: false },
    { name: 'hour "13" complete by length', key: 'hour', digits: '13', expected: true },
    { name: 'minute "6" auto-advances (60>59)', key: 'minute', digits: '6', expected: true },
    { name: 'minute "5" stays', key: 'minute', digits: '5', expected: false },
    { name: 'minute "59" complete', key: 'minute', digits: '59', expected: true }
  ])('$name', ({ key, digits, expected }) => {
    expect(timeField(24).isComplete(key, digits)).toBe(expected)
  })
})

describe('useTimeField.typeChar', () => {
  test.each<{ name: string; key: string; char: string; expected: string | undefined }>([
    { name: 'p selects PM', key: 'meridiem', char: 'p', expected: 'PM' },
    { name: 'P case-insensitive', key: 'meridiem', char: 'P', expected: 'PM' },
    { name: 'a selects AM', key: 'meridiem', char: 'a', expected: 'AM' },
    { name: 'unmatched char', key: 'meridiem', char: 'x', expected: undefined },
    { name: 'non-meridiem segment', key: 'hour', char: '1', expected: undefined }
  ])('$name', ({ key, char, expected }) => {
    const result = timeField(12).typeChar({}, key, char)
    if (expected === undefined) {
      expect(result).toBeUndefined()
    } else {
      expect(result?.meridiem).toBe(expected)
    }
  })
})

describe('useTimeField — reactive FieldType', () => {
  test('time 12h adds meridiem', () => {
    const field = timeField(12)
    expect(field.segments).toHaveLength(3)
    const last = field.segments[2]!
    expect(last.key).toBe('meridiem')
    expect(last.pad).toBeNull()
    expect(last.options).toEqual(['AM', 'PM'])
  })
  test('time h11 adds meridiem', () => {
    const field = timeField(11)
    expect(field.segments).toHaveLength(3)
    expect(field.segments[2]!.key).toBe('meridiem')
  })
  test('time 24h omits meridiem', () => {
    const field = timeField(24)
    expect(field.segments.map((segment) => segment.key)).toEqual(['hour', 'minute'])
  })
  test('hourCycle reactive', () => {
    const hourCycle = ref<HourCycle>(12)
    const field = useTimeField(() => hourCycle.value)
    expect(field.value.segments).toHaveLength(3)
    hourCycle.value = 24
    expect(field.value.segments.map((segment) => segment.key)).toEqual(['hour', 'minute'])
  })
})
