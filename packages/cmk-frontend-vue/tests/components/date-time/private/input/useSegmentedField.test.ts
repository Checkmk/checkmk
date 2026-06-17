/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type Ref, nextTick, ref, shallowRef } from 'vue'

import { useDateField } from '@/components/date-time/private/input/useDateField'
import {
  clampToRange,
  digitsAreComplete,
  parseSegment,
  selectInputOnFocus,
  useSegmentedField,
  wrapToRange
} from '@/components/date-time/private/input/useSegmentedField'
import { useTimeField } from '@/components/date-time/private/input/useTimeField'
import type { DateFormatParts, HourCycle, TimeValue } from '@/components/date-time/types'

import { DMY, MONTH_NAMES_EN, YMD } from '../../dateTimeTestFixtures'

const inputEvent = (value: string): Event => ({ target: { value } }) as unknown as Event
const keyEvent = (key: string): KeyboardEvent =>
  ({ key, preventDefault: vi.fn() }) as unknown as KeyboardEvent

const stubInput = (): HTMLInputElement => {
  const el = document.createElement('input')
  vi.spyOn(el, 'focus')
  vi.spyOn(el, 'select')
  return el
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('clampToRange', () => {
  test.each([
    { name: 'above max', value: 40, min: 1, max: 31, expected: 31 },
    { name: 'below min', value: 0, min: 1, max: 31, expected: 1 },
    { name: 'in range', value: 15, min: 1, max: 31, expected: 15 }
  ])('$name', ({ value, min, max, expected }) => {
    expect(clampToRange(value, min, max)).toBe(expected)
  })
})

describe('wrapToRange', () => {
  test.each([
    { name: 'over by one (0-based)', value: 24, min: 0, max: 23, expected: 0 },
    { name: 'under by one', value: -1, min: 0, max: 23, expected: 23 },
    { name: 'over by one (1-based)', value: 13, min: 1, max: 12, expected: 1 },
    { name: 'under by one (1-based)', value: 0, min: 1, max: 12, expected: 12 },
    { name: 'far over', value: 25, min: 0, max: 23, expected: 1 },
    { name: 'span 1', value: 7, min: 5, max: 5, expected: 5 }
  ])('$name', ({ value, min, max, expected }) => {
    expect(wrapToRange(value, min, max)).toBe(expected)
  })
})

describe('digitsAreComplete', () => {
  test.each([
    { name: 'already at max length', digits: '31', maxlen: 2, max: 31, expected: true },
    { name: '×10 exceeds max (40>31)', digits: '4', maxlen: 2, max: 31, expected: true },
    { name: 'can still grow (30≤31)', digits: '3', maxlen: 2, max: 31, expected: false },
    { name: 'hour "1" can grow (10≤23)', digits: '1', maxlen: 2, max: 23, expected: false },
    { name: 'minute "6" can\'t grow (60>59)', digits: '6', maxlen: 2, max: 59, expected: true }
  ])('$name', ({ digits, maxlen, max, expected }) => {
    expect(digitsAreComplete(digits, maxlen, max)).toBe(expected)
  })
})

describe('parseSegment', () => {
  test('empty → null', () => {
    expect(parseSegment('')).toBeNull()
  })
  test('digits → int', () => {
    expect(parseSegment('07')).toBe(7)
  })
})

describe('selectInputOnFocus', () => {
  test('input target selected', () => {
    const el = stubInput()
    selectInputOnFocus({ target: el } as unknown as FocusEvent)
    expect(el.select).toHaveBeenCalled()
  })
  test('null target is a no-op', () => {
    expect(() => selectInputOnFocus({ target: null } as unknown as FocusEvent)).not.toThrow()
  })
})

// --- the interaction engine -----------------------------------------------------------------

const dateEngine = (format: DateFormatParts | Ref<DateFormatParts> = DMY) => {
  // shallowRef (not ref): mirrors how the pickers hand the engine a model whose immutable
  // CalendarDate payload is never wrapped in a reactive proxy, so the own-echo identity check holds.
  const model = shallowRef<CalendarDate | null>(null)
  const commit = vi.fn()
  const carry = vi.fn()
  const navigateOut = vi.fn()
  const field = useDateField(
    () => (typeof format === 'object' && 'value' in format ? format.value : format),
    () => MONTH_NAMES_EN
  )
  const api = useSegmentedField(field, model, { commit, navigateOut, carry })
  const view = (key: string) => api.views.value.find((entry) => entry.key === key)!
  return { model, commit, carry, navigateOut, api, view }
}

const timeEngine = (hourCycle: HourCycle) => {
  const model = shallowRef<TimeValue | null>(null)
  const commit = vi.fn()
  const carry = vi.fn()
  const navigateOut = vi.fn()
  const field = useTimeField(() => hourCycle)
  const api = useSegmentedField(field, model, { commit, navigateOut, carry })
  const view = (key: string) => api.views.value.find((entry) => entry.key === key)!
  return { model, commit, carry, navigateOut, api, view }
}

describe('useSegmentedField — interaction engine', () => {
  test('views derive from spec.segments', () => {
    const { api } = dateEngine()
    expect(api.views.value.map((entry) => entry.key)).toEqual(['day', 'month', 'year'])
    expect(api.views.value[0]!.separator).toBe('')
  })

  test('onInput strips non-digits', () => {
    const { api, view } = dateEngine()
    api.onInput('day', inputEvent('1a2'))
    expect(view('day').text).toBe('12')
  })

  test('onInput auto-advances when complete', async () => {
    const { api, view } = dateEngine()
    const month = stubInput()
    api.registerInput('month', month)
    api.onInput('day', inputEvent('4'))
    expect(view('day').text).toBe('04')
    await nextTick()
    expect(month.focus).toHaveBeenCalled()
  })

  test('onInput on read-only segment ignored', () => {
    const { api, view } = timeEngine(12)
    const before = view('meridiem').text
    api.onInput('meridiem', inputEvent('5'))
    expect(view('meridiem').text).toBe(before)
  })

  test('ArrowUp steps +1', () => {
    const { api, view } = dateEngine()
    api.onKey('day', keyEvent('ArrowUp'))
    expect(view('day').text).toBe('01')
  })

  test('ArrowDown steps −1', async () => {
    const { api, view, model } = dateEngine()
    model.value = new CalendarDate(2026, 3, 15)
    await nextTick()
    api.onKey('day', keyEvent('ArrowDown'))
    expect(view('day').text).toBe('14')
  })

  test('arrow flushes pending digits first', () => {
    const { api, view } = dateEngine()
    api.onInput('day', inputEvent('1'))
    api.onKey('day', keyEvent('ArrowUp'))
    // '1' folded to '01' then stepped +1 → '02'
    expect(view('day').text).toBe('02')
  })

  test('arrow carry forwarded', async () => {
    const { api, carry, model } = timeEngine(24)
    model.value = { hour: 23, minute: 0 }
    await nextTick()
    api.onKey('hour', keyEvent('ArrowUp'))
    expect(carry).toHaveBeenCalledWith(1)
  })

  test('ArrowLeft moves focus −1', async () => {
    const { api } = dateEngine()
    const day = stubInput()
    api.registerInput('day', day)
    api.onKey('month', keyEvent('ArrowLeft'))
    await nextTick()
    expect(day.focus).toHaveBeenCalled()
  })

  test('ArrowRight moves focus +1', async () => {
    const { api } = dateEngine()
    const month = stubInput()
    api.registerInput('month', month)
    api.onKey('day', keyEvent('ArrowRight'))
    await nextTick()
    expect(month.focus).toHaveBeenCalled()
  })

  test('separator key advances', async () => {
    const { api } = dateEngine()
    const month = stubInput()
    api.registerInput('month', month)
    api.onKey('day', keyEvent('.'))
    await nextTick()
    expect(month.focus).toHaveBeenCalled()
  })

  test('Enter when dirty', () => {
    const { api, commit } = dateEngine()
    api.onInput('day', inputEvent('1'))
    api.onKey('day', keyEvent('Enter'))
    expect(commit).toHaveBeenCalledOnce()
  })

  test('Enter when not dirty', () => {
    const { api, commit, model, view } = dateEngine()
    api.onKey('day', keyEvent('Enter'))
    expect(commit).toHaveBeenCalledOnce()
    expect(model.value).toBeNull()
    expect(view('day').text).toBe('')
  })

  test('typeChar on read-only segment', () => {
    const { api, view } = timeEngine(12)
    api.onKey('meridiem', keyEvent('p'))
    expect(view('meridiem').text).toBe('PM')
  })

  test('typeChar no match', () => {
    const { api, view } = timeEngine(12)
    const before = view('meridiem').text
    api.onKey('meridiem', keyEvent('x'))
    expect(view('meridiem').text).toBe(before)
  })

  test('onBlur flushes dirty', () => {
    const { api, view } = dateEngine()
    api.onInput('day', inputEvent('2'))
    api.onBlur()
    expect(view('day').text).toBe('02')
  })

  test('onBlur not dirty', () => {
    const { api, view } = dateEngine()
    api.onBlur()
    expect(view('day').text).toBe('')
  })

  test('field focus-out normalizes display', () => {
    const { api, view } = dateEngine()
    const field = document.createElement('div')
    const outside = document.createElement('button')
    api.onInput('day', inputEvent('2'))
    api.onFieldFocusOut({ relatedTarget: outside, currentTarget: field } as unknown as FocusEvent)
    expect(view('day').text).toBe('02')
  })

  test('focus-out between own segments', () => {
    const { api, view } = dateEngine()
    const field = document.createElement('div')
    const inner = document.createElement('input')
    field.appendChild(inner)
    api.onInput('day', inputEvent('2'))
    api.onFieldFocusOut({ relatedTarget: inner, currentTarget: field } as unknown as FocusEvent)
    expect(view('day').text).toBe('2')
  })

  test('focus-out on window blur', () => {
    vi.spyOn(document, 'hasFocus').mockReturnValue(false)
    const { api, view } = dateEngine()
    const field = document.createElement('div')
    api.onInput('day', inputEvent('2'))
    api.onFieldFocusOut({ relatedTarget: null, currentTarget: field } as unknown as FocusEvent)
    expect(view('day').text).toBe('2')
  })

  test('model watch re-derives', async () => {
    const { view, model } = dateEngine()
    model.value = new CalendarDate(2026, 3, 9)
    await nextTick()
    expect(view('day').text).toBe('09')
    expect(view('year').text).toBe('2026')
  })

  test('model watch suppresses own echo', async () => {
    const { api, view } = dateEngine()
    // Complete a date so the engine commits and remembers the written value.
    api.onInput('day', inputEvent('09'))
    api.onInput('month', inputEvent('03'))
    api.onInput('year', inputEvent('2026'))
    // Type a fresh dirty edit before the model watch flushes its own echo.
    api.onInput('day', inputEvent('1'))
    await nextTick()
    // The echo (value === lastWritten) is suppressed, so the dirty edit survives.
    expect(view('day').text).toBe('1')
  })

  test('spec change re-derives + clears dirty', async () => {
    const format = ref<DateFormatParts>(DMY)
    const { api, view, model } = dateEngine(format)
    model.value = new CalendarDate(2026, 3, 9)
    await nextTick()
    api.onInput('day', inputEvent('1'))
    expect(view('day').text).toBe('1')
    format.value = YMD
    await nextTick()
    expect(view('day').text).toBe('09')
    expect(api.views.value.map((entry) => entry.key)).toEqual(['year', 'month', 'day'])
  })
})
