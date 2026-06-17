/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, test, vi } from 'vitest'
import { nextTick, shallowRef } from 'vue'

import {
  clampToRange,
  digitsAreComplete,
  parseSegment,
  selectInputOnFocus,
  useSegmentedField,
  wrapToRange
} from '@/components/date-time/private/input/useSegmentedField'
import { useTimeField } from '@/components/date-time/private/input/useTimeField'
import type { HourCycle, TimeValue } from '@/components/date-time/types'

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
  test('onInput on read-only segment ignored', () => {
    const { api, view } = timeEngine(12)
    const before = view('meridiem').text
    api.onInput('meridiem', inputEvent('5'))
    expect(view('meridiem').text).toBe(before)
  })

  test('arrow carry forwarded', async () => {
    const { api, carry, model } = timeEngine(24)
    model.value = { hour: 23, minute: 0 }
    await nextTick()
    api.onKey('hour', keyEvent('ArrowUp'))
    expect(carry).toHaveBeenCalledWith(1)
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
})
