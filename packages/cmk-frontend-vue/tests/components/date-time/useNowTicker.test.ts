/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { type EffectScope, type Ref, effectScope, nextTick, ref } from 'vue'

import { useNowTicker } from '@/components/date-time/useNowTicker'

// :10:23.400 — 23.4s into the minute, so the next minute boundary is 36.6s away.
const NOW = new Date('2026-06-10T10:10:23.400Z')

const MS_TO_BOUNDARY = 36600 // from NOW to the next whole minute
const BOUNDARY_MARGIN_MS = 50 // the ticker fires just *past* the boundary, never exactly on it
const MS_TO_FIRST_TICK = MS_TO_BOUNDARY + BOUNDARY_MARGIN_MS // 36650
const ONE_MINUTE_MS = 60000

let scope: EffectScope

const run = (active: Ref<boolean>): Ref<Date> => {
  scope = effectScope()
  return scope.run(() => useNowTicker(active))!
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})

afterEach(() => {
  scope?.stop()
  vi.useRealTimers()
})

describe('useNowTicker', () => {
  test('inactive ⇒ no timer', () => {
    const now = run(ref(false))
    expect(now.value.getTime()).toBe(NOW.getTime())
    expect(vi.getTimerCount()).toBe(0)
  })

  test('activate re-reads now and schedules the tick', async () => {
    const active = ref(false)
    const now = run(active)
    // While inactive, now stays frozen at construction time even as the wall clock advances.
    vi.setSystemTime(new Date('2026-06-10T10:10:53.400Z')) // +30s
    expect(now.value.getTime()).toBe(NOW.getTime())
    // Activating re-reads the wall clock and schedules the next-minute tick. The exact +50ms
    // landing past the boundary is covered by 'the scheduled delay lands +50ms past the boundary'.
    active.value = true
    await nextTick()
    expect(now.value.toISOString()).toBe('2026-06-10T10:10:53.400Z')
    expect(vi.getTimerCount()).toBe(1)
  })

  test('tick re-reads on the minute and reschedules ~60s', async () => {
    const active = ref(true)
    const now = run(active)
    await nextTick()
    vi.advanceTimersByTime(MS_TO_FIRST_TICK)
    expect(now.value.toISOString()).toBe('2026-06-10T10:11:00.050Z')
    // A fresh timer is pending for the next minute.
    expect(vi.getTimerCount()).toBe(1)
  })

  test('each tick reschedules ~60s (never per-second)', async () => {
    const active = ref(true)
    const now = run(active)
    await nextTick()
    vi.advanceTimersByTime(MS_TO_FIRST_TICK) // → :11:00.050
    expect(now.value.getUTCMinutes()).toBe(11)
    vi.advanceTimersByTime(ONE_MINUTE_MS) // → :12:00.050
    expect(now.value.getUTCMinutes()).toBe(12)
    expect(now.value.getUTCSeconds()).toBe(0)
  })

  test('deactivate clears the pending timeout and freezes now', async () => {
    const active = ref(true)
    const now = run(active)
    await nextTick()
    const frozen = now.value.getTime()
    active.value = false
    await nextTick()
    expect(vi.getTimerCount()).toBe(0)
    vi.advanceTimersByTime(120000)
    expect(now.value.getTime()).toBe(frozen)
  })

  test('scope dispose clears the timeout', async () => {
    const active = ref(true)
    const now = run(active)
    await nextTick()
    const frozen = now.value.getTime()
    scope.stop()
    expect(vi.getTimerCount()).toBe(0)
    vi.advanceTimersByTime(120000)
    expect(now.value.getTime()).toBe(frozen)
  })

  test('the scheduled delay lands +50ms past the boundary', async () => {
    const active = ref(true)
    const now = run(active)
    await nextTick()
    // Exactly at the minute boundary the timer has not fired yet.
    vi.advanceTimersByTime(MS_TO_BOUNDARY)
    expect(now.value.getTime()).toBe(NOW.getTime())
    vi.advanceTimersByTime(BOUNDARY_MARGIN_MS - 1)
    expect(now.value.getTime()).toBe(NOW.getTime())
    vi.advanceTimersByTime(1) // total MS_TO_FIRST_TICK → fires
    expect(now.value.getUTCMinutes()).toBe(11)
  })
})
