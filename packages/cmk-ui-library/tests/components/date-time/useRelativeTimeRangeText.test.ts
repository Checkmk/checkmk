/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useRelativeTimeRangeText } from 'cmk-ui-library/components/date-time/useRelativeTimeRangeText'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { type EffectScope, effectScope, ref } from 'vue'

const NOW = new Date('2026-06-26T18:30:30Z')
const ONE_MINUTE_MS = 60000

let scope: EffectScope

const run = (active: boolean): ((durationSeconds: number | null) => string | null) => {
  scope = effectScope()
  return scope.run(() => useRelativeTimeRangeText(ref(active), 'UTC'))!
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})

afterEach(() => {
  scope?.stop()
  vi.useRealTimers()
})

describe('useRelativeTimeRangeText', () => {
  test('is null without a duration', () => {
    expect(run(true)(null)).toBeNull()
  })

  test('follows the clock while active', () => {
    const rangeText = run(true)
    const before = rangeText(4 * 3600)

    vi.advanceTimersByTime(ONE_MINUTE_MS)

    expect(rangeText(4 * 3600)).not.toBe(before)
  })

  test('keeps its text while inactive', () => {
    const rangeText = run(false)
    const before = rangeText(4 * 3600)

    vi.advanceTimersByTime(ONE_MINUTE_MS)

    expect(rangeText(4 * 3600)).toBe(before)
  })
})
