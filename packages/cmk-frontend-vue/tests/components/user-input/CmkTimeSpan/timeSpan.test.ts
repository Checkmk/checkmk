/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { formatTimeSpan } from '@/components/user-input/CmkTimeSpan/timeSpan'

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
