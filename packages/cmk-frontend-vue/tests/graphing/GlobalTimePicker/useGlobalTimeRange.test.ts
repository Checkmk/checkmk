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
  resetGlobalRefresh,
  useGlobalRefresh
} from '@/graphing/GlobalRefreshControl/useGlobalRefresh'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'
import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/useGlobalTimeRange'

const TZ = 'Europe/Berlin'
const zoned = (day: number): ZonedDateTime =>
  toZoned(new CalendarDateTime(2026, 3, day, 0, 0), TZ, 'compatible')
const range = (fromDay: number, toDay: number): DateTimeRange => ({
  from: zoned(fromDay),
  to: zoned(toDay)
})

describe('useGlobalTimeRange', () => {
  // The store is a module-level singleton shared across the whole bundle; reset it so each test
  // starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null)
  })

  test('starts as null', () => {
    expect(useGlobalTimeRange().activeTimeRange.value).toBeNull()
  })

  test('a write is visible to a second consumer', () => {
    const writer = useGlobalTimeRange()
    const reader = useGlobalTimeRange()
    writer.setActiveTimeRange(range(9, 10))
    expect(reader.activeTimeRange.value).toEqual(range(9, 10))
  })

  test('a write reactively triggers a second consumer', async () => {
    const reader = useGlobalTimeRange()
    const seen: Array<DateTimeRange | null> = []
    watch(reader.activeTimeRange, (value) => seen.push(value))

    // A write through a separate consumer (e.g. a graph panning) is observed by the reader.
    useGlobalTimeRange().setActiveTimeRange(range(9, 10))
    await nextTick()
    expect(seen).toEqual([range(9, 10)])
  })

  describe('pausing the global refresh', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      // Noon on the 10th: range(9, 10) has ended, range(10, 11) has not.
      vi.setSystemTime(zoned(10).add({ hours: 12 }).toDate())
      resetGlobalRefresh()
      useGlobalRefresh().setRefreshPaused(false)
    })

    afterEach(() => {
      resetGlobalRefresh()
      vi.useRealTimers()
    })

    test('a range that already ended pauses the refresh', () => {
      useGlobalTimeRange().setActiveTimeRange(range(9, 10))

      expect(useGlobalRefresh().refreshPaused.value).toBe(true)
    })

    test('a range ending now keeps the refresh running', () => {
      useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600))

      expect(useGlobalRefresh().refreshPaused.value).toBe(false)
    })

    test('a range ending in the future keeps the refresh running', () => {
      // The "Today" quick range shape: ends at the end of the day.
      useGlobalTimeRange().setActiveTimeRange(range(10, 11))

      expect(useGlobalRefresh().refreshPaused.value).toBe(false)
    })

    test('going back to a range ending now does not resume the refresh', () => {
      useGlobalTimeRange().setActiveTimeRange(range(9, 10))

      useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600))

      expect(useGlobalRefresh().refreshPaused.value).toBe(true)
    })

    test('resuming while a range that already ended is selected keeps that range', () => {
      const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
      setActiveTimeRange(range(9, 10))

      useGlobalRefresh().setRefreshPaused(false)

      expect(useGlobalRefresh().refreshPaused.value).toBe(false)
      expect(activeTimeRange.value).toEqual(range(9, 10))
    })
  })
})
