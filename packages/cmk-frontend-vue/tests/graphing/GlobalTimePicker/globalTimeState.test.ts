/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick, watch } from 'vue'

import {
  resetGlobalTimeState,
  seedRefreshIntervalSeconds,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'

const TZ = 'Europe/Berlin'
const zoned = (day: number): ZonedDateTime =>
  toZoned(new CalendarDateTime(2026, 3, day, 0, 0), TZ, 'compatible')
const range = (fromDay: number, toDay: number): DateTimeRange => ({
  from: zoned(fromDay),
  to: zoned(toDay)
})

describe('the refresh clock', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
    vi.useRealTimers()
  })

  test('starts paused with the default interval', () => {
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
  })

  test('a write is visible to a second consumer', () => {
    const writer = useGlobalRefresh()
    const reader = useGlobalRefresh()

    writer.setRefreshIntervalSeconds(60)

    expect(reader.refreshIntervalSeconds.value).toBe(60)
  })

  test('resuming refreshes immediately, then ticks at the configured interval', () => {
    const { setRefreshPaused, refreshTick } = useGlobalRefresh()
    const ticksBefore = refreshTick.value

    setRefreshPaused(false)
    expect(refreshTick.value).toBe(ticksBefore + 1)

    vi.advanceTimersByTime(30_000)
    expect(refreshTick.value).toBe(ticksBefore + 2)

    vi.advanceTimersByTime(60_000)
    expect(refreshTick.value).toBe(ticksBefore + 4)
  })

  test('pausing stops the timer and keeps the interval', () => {
    const { setRefreshPaused, refreshIntervalSeconds, refreshTick } = useGlobalRefresh()
    setRefreshPaused(false)
    vi.advanceTimersByTime(30_000)
    const ticksWhenPaused = refreshTick.value

    setRefreshPaused(true)
    vi.advanceTimersByTime(90_000)

    expect(refreshTick.value).toBe(ticksWhenPaused)
    expect(refreshIntervalSeconds.value).toBe(30)
  })

  test('changing the interval restarts the timer without an immediate refresh', () => {
    const { setRefreshIntervalSeconds, setRefreshPaused, refreshTick } = useGlobalRefresh()
    setRefreshPaused(false)
    vi.advanceTimersByTime(20_000)
    const ticksBefore = refreshTick.value

    setRefreshIntervalSeconds(60)
    expect(refreshTick.value).toBe(ticksBefore)

    vi.advanceTimersByTime(30_000)
    expect(refreshTick.value).toBe(ticksBefore)
    vi.advanceTimersByTime(30_000)
    expect(refreshTick.value).toBe(ticksBefore + 1)
  })

  test('changing the interval while paused does not start the timer', () => {
    const { setRefreshIntervalSeconds, refreshTick } = useGlobalRefresh()
    const ticksBefore = refreshTick.value

    setRefreshIntervalSeconds(60)
    vi.advanceTimersByTime(120_000)

    expect(refreshTick.value).toBe(ticksBefore)
  })

  test('seeding a preferred interval preselects it without starting the timer', () => {
    const { refreshIntervalSeconds, refreshPaused, refreshTick } = useGlobalRefresh()
    const ticksBefore = refreshTick.value

    seedRefreshIntervalSeconds(60)
    vi.advanceTimersByTime(120_000)

    expect(refreshIntervalSeconds.value).toBe(60)
    expect(refreshPaused.value).toBe(true)
    expect(refreshTick.value).toBe(ticksBefore)
  })

  test('seeding null keeps the default interval', () => {
    seedRefreshIntervalSeconds(null)
    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
  })

  test('only the first seed wins', () => {
    seedRefreshIntervalSeconds(60)
    seedRefreshIntervalSeconds(90)
    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
  })

  test('a bogus value does not consume the one-shot', () => {
    seedRefreshIntervalSeconds(Number.NaN)
    seedRefreshIntervalSeconds(60)

    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
  })
})

describe('useGlobalTimeRange', () => {
  // The store is a module-level singleton shared across the whole bundle; reset it so each test
  // starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
  })

  test('starts as null', () => {
    expect(useGlobalTimeRange().activeTimeRange.value).toBeNull()
  })

  test('a write is visible to a second consumer', () => {
    const writer = useGlobalTimeRange()
    const reader = useGlobalTimeRange()
    writer.setActiveTimeRange(range(9, 10), 'time_picker')
    expect(reader.activeTimeRange.value).toEqual(range(9, 10))
  })

  test('a write reactively triggers a second consumer', async () => {
    const reader = useGlobalTimeRange()
    const seen: Array<DateTimeRange | null> = []
    watch(reader.activeTimeRange, (value) => seen.push(value))

    // A write through a separate consumer (e.g. a graph panning) is observed by the reader.
    useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')
    await nextTick()
    expect(seen).toEqual([range(9, 10)])
  })

  describe('the origin of the active range', () => {
    test('starts out attributed to the time picker', () => {
      expect(useGlobalTimeRange().activeTimeRangeState.value).toEqual({
        range: null,
        origin: 'time_picker'
      })
    })

    test.each(['time_picker', 'external'] as const)(
      'a write records the %s origin it was given',
      (origin) => {
        useGlobalTimeRange().setActiveTimeRange(range(9, 10), origin)

        expect(useGlobalTimeRange().activeTimeRangeState.value.origin).toBe(origin)
      }
    )

    test('the range and its origin become visible in the same update', async () => {
      const reader = useGlobalTimeRange()
      const seen: Array<{ fromDay: number | null; origin: string }> = []
      const stopWatching = watch(reader.activeTimeRangeState, ({ range: published, origin }) => {
        seen.push({ fromDay: published === null ? null : published.from.day, origin })
      })

      useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'external')
      await nextTick()
      stopWatching()

      expect(seen).toEqual([{ fromDay: 9, origin: 'external' }])
    })
  })

  describe('pausing the global refresh', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      // Noon on the 10th: range(9, 10) has ended, range(10, 11) has not.
      vi.setSystemTime(zoned(10).add({ hours: 12 }).toDate())
      resetGlobalTimeState()
      useGlobalRefresh().setRefreshPaused(false)
    })

    afterEach(() => {
      resetGlobalTimeState()
      vi.useRealTimers()
    })

    test('a range that already ended pauses the refresh', () => {
      useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')

      expect(useGlobalRefresh().refreshPaused.value).toBe(true)
    })

    test('a range ending now keeps the refresh running', () => {
      useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')

      expect(useGlobalRefresh().refreshPaused.value).toBe(false)
    })

    test('a range ending in the future keeps the refresh running', () => {
      // The "Today" quick range shape: ends at the end of the day.
      useGlobalTimeRange().setActiveTimeRange(range(10, 11), 'time_picker')

      expect(useGlobalRefresh().refreshPaused.value).toBe(false)
    })

    test('going back to a range ending now does not resume the refresh', () => {
      useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')

      useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')

      expect(useGlobalRefresh().refreshPaused.value).toBe(true)
    })

    test('resuming while a range that already ended is selected keeps that range', () => {
      const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
      setActiveTimeRange(range(9, 10), 'time_picker')

      useGlobalRefresh().setRefreshPaused(false)

      expect(useGlobalRefresh().refreshPaused.value).toBe(false)
      expect(activeTimeRange.value).toEqual(range(9, 10))
    })
  })
})
