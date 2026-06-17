/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { describe, expect, test } from 'vitest'
import { ref } from 'vue'

import { useDateField } from '@/components/date-time/private/input/useDateField'
import type { SegmentText } from '@/components/date-time/private/input/useSegmentedField'
import type { DateFormatParts } from '@/components/date-time/types'

import { DMY, MONTH_NAMES_EN, YMD } from '../../dateTimeTestFixtures'

const dateField = (format: DateFormatParts = DMY) =>
  useDateField(
    () => format,
    () => MONTH_NAMES_EN
  ).value

describe('useDateField.toValue', () => {
  test.each<{ name: string; text: SegmentText; expected: string | null }>([
    { name: 'valid', text: { day: '09', month: '03', year: '2026' }, expected: '2026-03-09' },
    {
      name: 'leap day valid',
      text: { day: '29', month: '02', year: '2024' },
      expected: '2024-02-29'
    },
    {
      name: 'Feb 29 non-leap → null',
      text: { day: '29', month: '02', year: '2023' },
      expected: null
    },
    { name: 'Feb 30 → null', text: { day: '30', month: '02', year: '2024' }, expected: null },
    { name: 'Apr 31 → null', text: { day: '31', month: '04', year: '2024' }, expected: null },
    { name: 'day empty → null', text: { day: '', month: '03', year: '2026' }, expected: null },
    { name: 'month empty → null', text: { day: '09', month: '', year: '2026' }, expected: null },
    { name: 'year empty → null', text: { day: '09', month: '03', year: '' }, expected: null }
  ])('$name', ({ text, expected }) => {
    const result = dateField().toValue(text)
    if (expected === null) {
      expect(result).toBeNull()
    } else {
      expect(result?.toString()).toBe(expected)
    }
  })
})

describe('useDateField.toText', () => {
  test('null → empty strings', () => {
    expect(dateField().toText(null, {})).toEqual({ day: '', month: '', year: '' })
  })
  test('date → padded', () => {
    expect(dateField().toText(new CalendarDate(2026, 3, 9), {})).toEqual({
      day: '09',
      month: '03',
      year: '2026'
    })
  })
  test('sub-1000 year padded', () => {
    expect(dateField().toText(new CalendarDate(99, 3, 9), {})).toEqual({
      day: '09',
      month: '03',
      year: '0099'
    })
  })
})

describe('useDateField.normalize', () => {
  test.each<{ name: string; text: SegmentText; expected: SegmentText }>([
    {
      name: 'day over static max → 31',
      text: { day: '40', month: '', year: '' },
      expected: { day: '31', month: '', year: '' }
    },
    {
      name: 'zero → min',
      text: { day: '00', month: '', year: '' },
      expected: { day: '01', month: '', year: '' }
    },
    {
      name: 'month over max → 12',
      text: { day: '', month: '13', year: '' },
      expected: { day: '', month: '12', year: '' }
    },
    {
      name: 'empty stays empty',
      text: { day: '', month: '', year: '' },
      expected: { day: '', month: '', year: '' }
    },
    {
      name: 'complete impossible day snaps to month',
      text: { day: '31', month: '02', year: '2026' },
      expected: { day: '28', month: '02', year: '2026' }
    },
    {
      name: 'complete day over 30-day month → 30',
      text: { day: '31', month: '04', year: '2026' },
      expected: { day: '30', month: '04', year: '2026' }
    },
    {
      name: 'complete leap keeps 29',
      text: { day: '29', month: '02', year: '2024' },
      expected: { day: '29', month: '02', year: '2024' }
    },
    {
      name: 'complete in range → no-op',
      text: { day: '15', month: '02', year: '2026' },
      expected: { day: '15', month: '02', year: '2026' }
    },
    {
      name: 'partial (no year) not day-snapped',
      text: { day: '31', month: '02', year: '' },
      expected: { day: '31', month: '02', year: '' }
    }
  ])('$name', ({ text, expected }) => {
    expect(dateField().normalize(text)).toEqual(expected)
  })
})

describe('useDateField.step — complete date', () => {
  test.each<{ name: string; text: SegmentText; key: string; delta: 1 | -1; expected: SegmentText }>(
    [
      {
        name: 'Jan 31 +1 month → leap Feb 29',
        text: { day: '31', month: '01', year: '2024' },
        key: 'month',
        delta: 1,
        expected: { day: '29', month: '02', year: '2024' }
      },
      {
        name: 'Jan 31 +1 month → non-leap 28',
        text: { day: '31', month: '01', year: '2023' },
        key: 'month',
        delta: 1,
        expected: { day: '28', month: '02', year: '2023' }
      },
      {
        name: 'Feb 29 +1 year → clamp 28',
        text: { day: '29', month: '02', year: '2024' },
        key: 'year',
        delta: 1,
        expected: { day: '28', month: '02', year: '2025' }
      },
      {
        name: 'Dec 31 +1 day → next year',
        text: { day: '31', month: '12', year: '2024' },
        key: 'day',
        delta: 1,
        expected: { day: '01', month: '01', year: '2025' }
      },
      {
        name: 'Dec +1 month → next year',
        text: { day: '15', month: '12', year: '2024' },
        key: 'month',
        delta: 1,
        expected: { day: '15', month: '01', year: '2025' }
      }
    ]
  )('$name', ({ text, key, delta, expected }) => {
    expect(dateField().step(text, key, delta).text).toEqual(expected)
  })
})

describe('useDateField.step — incomplete date', () => {
  test.each<{ name: string; text: SegmentText; key: string; delta: 1 | -1; expected: string }>([
    {
      name: 'null part initializes to min',
      text: { day: '', month: '', year: '' },
      key: 'day',
      delta: 1,
      expected: '01'
    },
    {
      name: 'year clamps at max',
      text: { day: '', month: '', year: '9999' },
      key: 'year',
      delta: 1,
      expected: '9999'
    },
    {
      name: 'year clamps at min',
      text: { day: '', month: '', year: '0001' },
      key: 'year',
      delta: -1,
      expected: '0001'
    },
    {
      name: 'day wraps within [1,31] (month empty)',
      text: { day: '31', month: '', year: '' },
      key: 'day',
      delta: 1,
      expected: '01'
    },
    {
      name: 'month wraps when incomplete',
      text: { day: '', month: '12', year: '' },
      key: 'month',
      delta: 1,
      expected: '01'
    },
    {
      name: 'day wraps static [1,31], not month-aware',
      text: { day: '28', month: '02', year: '' },
      key: 'day',
      delta: 1,
      expected: '29'
    }
  ])('$name', ({ text, key, delta, expected }) => {
    expect(dateField().step(text, key, delta).text[key]).toBe(expected)
  })
})

describe('useDateField.isComplete', () => {
  test.each([
    { name: 'day "4" auto-advances (40>31)', key: 'day', digits: '4', expected: true },
    { name: 'day "3" stays (31 reachable)', key: 'day', digits: '3', expected: false },
    { name: 'day "31" complete by length', key: 'day', digits: '31', expected: true },
    { name: 'month "2" auto-advances (20>12)', key: 'month', digits: '2', expected: true },
    { name: 'year needs 4 digits', key: 'year', digits: '202', expected: false },
    { name: 'year 4 digits complete', key: 'year', digits: '2026', expected: true }
  ])('$name', ({ key, digits, expected }) => {
    expect(dateField().isComplete(key, digits)).toBe(expected)
  })
})

describe('useDateField — reactive FieldType', () => {
  test('date segments follow order', () => {
    const field = useDateField(
      () => ({ order: ['month', 'day', 'year'], separator: '/' }),
      () => MONTH_NAMES_EN
    ).value
    expect(field.segments.map((segment) => segment.key)).toEqual(['month', 'day', 'year'])
    expect(field.separator).toBe('/')
  })
  test('date format reactive', () => {
    const format = ref<DateFormatParts>(DMY)
    const field = useDateField(
      () => format.value,
      () => MONTH_NAMES_EN
    )
    expect(field.value.segments.map((segment) => segment.key)).toEqual(['day', 'month', 'year'])
    format.value = YMD
    expect(field.value.segments.map((segment) => segment.key)).toEqual(['year', 'month', 'day'])
    expect(field.value.separator).toBe('-')
  })
})
