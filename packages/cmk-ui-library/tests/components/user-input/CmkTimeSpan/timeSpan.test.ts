/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  formatTimeSpan,
  minimumSecondsValidator
} from 'cmk-ui-library/components/user-input/CmkTimeSpan/timeSpan'
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

// Test double for _t: returns the msgid, interpolating any %{name} tokens.
const _t = (msg: string, interpolation: Record<string, string | number> = {}): string =>
  msg.replace(/%\{(\w+)\}/g, (_match, key) => String(interpolation[key]))

describe('formatTimeSpan', () => {
  const labels = { hour: 'Hours', minute: 'Minutes', second: 'Seconds' }

  it('renders one part per non-empty magnitude', () => {
    expect(formatTimeSpan(5400, ['hour', 'minute', 'second'], labels)).toBe('1 Hours 30 Minutes')
  })

  it('rounds the last displayed magnitude but floors the rest', () => {
    // 90s with only minutes displayed rounds 1.5 -> 2
    expect(formatTimeSpan(90, ['minute'], labels)).toBe('2 Minutes')
    // with seconds available the minute is floored and the remainder shown
    expect(formatTimeSpan(90, ['minute', 'second'], labels)).toBe('1 Minutes 30 Seconds')
  })

  it('returns an empty string when the value rounds to nothing', () => {
    expect(formatTimeSpan(0, ['hour', 'minute', 'second'], labels)).toBe('')
  })

  it('orders parts by magnitude regardless of the displayed order', () => {
    expect(formatTimeSpan(3601, ['second', 'hour'], labels)).toBe('1 Hours 1 Seconds')
  })

  it('falls back to the magnitude key when a label is missing', () => {
    expect(formatTimeSpan(3600, ['hour'], {})).toBe('1 hour')
  })

  it('unwraps ref and getter labels (MaybeRefOrGetter)', () => {
    expect(formatTimeSpan(3600, ['hour'], { hour: ref('Hrs') })).toBe('1 Hrs')
    expect(formatTimeSpan(3600, ['hour'], { hour: () => 'Hr' })).toBe('1 Hr')
  })
})

describe('minimumSecondsValidator', () => {
  const validate = minimumSecondsValidator(1, ['minute', 'second'], _t)

  it.each([
    { seconds: null, expected: [] },
    { seconds: 1, expected: [] },
    { seconds: 0.5, expected: ['The time span must be at least 1 Seconds.'] }
  ])('validates $seconds', ({ seconds, expected }) => {
    expect(validate(seconds)).toEqual(expected)
  })
})
