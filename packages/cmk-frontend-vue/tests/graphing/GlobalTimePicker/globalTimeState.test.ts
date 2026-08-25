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
  initGlobalRefresh,
  resetGlobalTimeState,
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

// Noon on the 10th: range(9, 10) has ended, range(10, 11) reaches into the future.
const NOON_ON_THE_TENTH = zoned(10).add({ hours: 12 }).toDate()

/** In ms, read back from the state instead of hardcoding the default. */
const oneIntervalMs = (): number => useGlobalRefresh().refreshIntervalSeconds.value * 1000

// Module-level singleton: reset it so each test starts from a known state.
beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOON_ON_THE_TENTH)
  resetGlobalTimeState()
})

afterEach(() => {
  resetGlobalTimeState()
  vi.useRealTimers()
})

describe('the published window', () => {
  test('nothing is published until someone publishes', () => {
    expect(useGlobalTimeRange().activeTimeRange.value).toBeNull()
  })

  test('a write is visible to every consumer', () => {
    const writer = useGlobalTimeRange()
    const reader = useGlobalTimeRange()

    writer.setActiveTimeRange(range(9, 10), 'time_picker')

    expect(reader.activeTimeRange.value).toEqual(range(9, 10))
  })

  test.each(['time_picker', 'external'] as const)(
    'a write records the %s origin it was given',
    (origin) => {
      useGlobalTimeRange().setActiveTimeRange(range(9, 10), origin)

      expect(useGlobalTimeRange().activeTimeRangeState.value.origin).toBe(origin)
    }
  )

  test('the window and its origin become visible in the same update', async () => {
    const { activeTimeRangeState, setActiveTimeRange } = useGlobalTimeRange()
    const seen: Array<{ fromDay: number | null; origin: string }> = []
    const stopWatching = watch(activeTimeRangeState, ({ range: published, origin }) => {
      seen.push({ fromDay: published === null ? null : published.from.day, origin })
    })

    setActiveTimeRange(range(9, 10), 'external')
    await nextTick()

    stopWatching()
    expect(seen).toEqual([{ fromDay: 9, origin: 'external' }])
  })
})

describe('a window that pauses the clock', () => {
  beforeEach(() => {
    useGlobalRefresh().resumeRefresh()
  })

  test('a window that already ended cannot gain data, so the refresh stops', () => {
    useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')

    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })

  test('a window reaching into the future still covers the present, so it keeps running', () => {
    // The "Today" quick range shape: ends at the end of the day.
    useGlobalTimeRange().setActiveTimeRange(range(10, 11), 'time_picker')

    expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  })

  test('going back to a live window does not resume it - that stays the user call', () => {
    useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')

    useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')

    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })
})

describe('the clock', () => {
  test('starts paused', () => {
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })

  test('resuming refreshes at once, because live data means now', () => {
    const { resumeRefresh, refreshTick } = useGlobalRefresh()
    const ticksBefore = refreshTick.value

    resumeRefresh()

    expect(refreshTick.value).toBe(ticksBefore + 1)
  })

  test('a running clock refreshes once per interval', () => {
    const { resumeRefresh, refreshTick } = useGlobalRefresh()
    resumeRefresh()
    const ticksBefore = refreshTick.value

    vi.advanceTimersByTime(3 * oneIntervalMs())

    expect(refreshTick.value).toBe(ticksBefore + 3)
  })

  test('pausing stops it', () => {
    const { resumeRefresh, pauseRefresh, refreshTick } = useGlobalRefresh()
    resumeRefresh()
    const ticksWhenPaused = refreshTick.value

    pauseRefresh()
    vi.advanceTimersByTime(3 * oneIntervalMs())

    expect(refreshTick.value).toBe(ticksWhenPaused)
  })

  test('choosing an interval does not refresh', () => {
    const { resumeRefresh, setRefreshIntervalSeconds, refreshIntervalSeconds, refreshTick } =
      useGlobalRefresh()
    resumeRefresh()
    const ticksBefore = refreshTick.value

    setRefreshIntervalSeconds(refreshIntervalSeconds.value * 3)

    expect(refreshTick.value).toBe(ticksBefore)
  })

  test('choosing an interval re-times the clock instead of adding to it', () => {
    const { resumeRefresh, setRefreshIntervalSeconds, refreshIntervalSeconds } = useGlobalRefresh()
    resumeRefresh()
    const previousIntervalMs = oneIntervalMs()
    setRefreshIntervalSeconds(refreshIntervalSeconds.value * 3)
    const ticksBefore = useGlobalRefresh().refreshTick.value

    vi.advanceTimersByTime(previousIntervalMs)

    expect(useGlobalRefresh().refreshTick.value).toBe(ticksBefore)
  })

  test('choosing an interval while paused leaves it paused', () => {
    const { setRefreshIntervalSeconds, refreshIntervalSeconds, refreshTick } = useGlobalRefresh()
    const ticksBefore = refreshTick.value

    setRefreshIntervalSeconds(refreshIntervalSeconds.value * 3)
    vi.advanceTimersByTime(3 * oneIntervalMs())

    expect(refreshTick.value).toBe(ticksBefore)
  })
})

describe('wiring the page', () => {
  const FROM_THE_SERVER = 60

  test('what the server just rendered is not refreshed on arrival', () => {
    const { refreshTick, refreshPaused } = useGlobalRefresh()

    initGlobalRefresh({ intervalSeconds: FROM_THE_SERVER, live: true })

    expect(refreshTick.value).toBe(0)
    expect(refreshPaused.value).toBe(false)
  })

  test('a page that arrives live refreshes once its own interval is up', () => {
    const { refreshTick } = useGlobalRefresh()
    initGlobalRefresh({ intervalSeconds: FROM_THE_SERVER, live: true })

    vi.advanceTimersByTime(FROM_THE_SERVER * 1000)

    expect(refreshTick.value).toBe(1)
  })

  test('a page that does not arrive live only preselects the interval', () => {
    const { refreshIntervalSeconds, refreshPaused, refreshTick } = useGlobalRefresh()

    initGlobalRefresh({ intervalSeconds: FROM_THE_SERVER, live: false })
    vi.advanceTimersByTime(3 * FROM_THE_SERVER * 1000)

    expect(refreshIntervalSeconds.value).toBe(FROM_THE_SERVER)
    expect(refreshPaused.value).toBe(true)
    expect(refreshTick.value).toBe(0)
  })

  test.each([null, Number.NaN, 0, -30])(
    'a page offering %s as its interval keeps the default',
    (intervalSeconds) => {
      const { refreshIntervalSeconds } = useGlobalRefresh()
      const theDefault = refreshIntervalSeconds.value

      initGlobalRefresh({ intervalSeconds, live: false })

      expect(refreshIntervalSeconds.value).toBe(theDefault)
    }
  )

  test('only the first wiring wins, so a late host cannot clobber it', () => {
    const { refreshIntervalSeconds, refreshPaused } = useGlobalRefresh()
    initGlobalRefresh({ intervalSeconds: FROM_THE_SERVER, live: false })

    initGlobalRefresh({ intervalSeconds: FROM_THE_SERVER * 2, live: true })

    expect(refreshIntervalSeconds.value).toBe(FROM_THE_SERVER)
    expect(refreshPaused.value).toBe(true)
  })
})
