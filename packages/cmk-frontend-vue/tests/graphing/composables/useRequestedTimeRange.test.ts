/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  CalendarDateTime,
  type ZonedDateTime,
  getLocalTimeZone,
  toZoned
} from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { nextTick } from 'vue'

import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/globalTimeState'
import { useRequestedTimeRange } from '@/graphing/composables/useRequestedTimeRange'

const TZ = 'Europe/Berlin'
const zoned = (day: number): ZonedDateTime =>
  toZoned(new CalendarDateTime(2026, 3, day, 0, 0), TZ, 'compatible')
const range = (fromDay: number, toDay: number): DateTimeRange => ({
  from: zoned(fromDay),
  to: zoned(toDay)
})
const epochSeconds = (value: ZonedDateTime): number => Math.floor(value.toDate().getTime() / 1000)

const INITIAL = { start: 1_000, end: 2_000 }

describe('useRequestedTimeRange', () => {
  // The global picker store is a module-level singleton shared across the whole bundle; reset it
  // so each test starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
  })

  test('seeds from initial when no global range is published', () => {
    const { requestedTimeRange } = useRequestedTimeRange(INITIAL)
    expect(requestedTimeRange.value).toEqual(INITIAL)
  })

  test('seeds from the global picker when it has already published a range', () => {
    const published = range(9, 10)
    useGlobalTimeRange().setActiveTimeRange(published, 'time_picker')

    const { requestedTimeRange } = useRequestedTimeRange(INITIAL)

    expect(requestedTimeRange.value).toEqual({
      start: epochSeconds(published.from),
      end: epochSeconds(published.to)
    })
  })

  test('follows a global picker change published after setup', async () => {
    const { requestedTimeRange } = useRequestedTimeRange(INITIAL)

    const published = range(9, 10)
    useGlobalTimeRange().setActiveTimeRange(published, 'time_picker')
    await nextTick()

    expect(requestedTimeRange.value).toEqual({
      start: epochSeconds(published.from),
      end: epochSeconds(published.to)
    })
  })

  test('keeps the last range when the global picker resets to null', async () => {
    const { requestedTimeRange } = useRequestedTimeRange(INITIAL)
    useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')
    await nextTick()
    const last = { ...requestedTimeRange.value }

    useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
    await nextTick()

    expect(requestedTimeRange.value).toEqual(last)
  })

  test('records a local update', () => {
    const { requestedTimeRange, setRequestedTimeRange } = useRequestedTimeRange(INITIAL)

    setRequestedTimeRange({ start: 5_000, end: 6_000 })

    expect(requestedTimeRange.value).toEqual({ start: 5_000, end: 6_000 })
  })

  test('publishes a local update as external, never as the picker', async () => {
    const { setRequestedTimeRange } = useRequestedTimeRange(INITIAL)

    setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()

    expect(useGlobalTimeRange().activeTimeRangeState.value.origin).toBe('external')
  })

  test('publishes a local update to the global picker', async () => {
    useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')
    const { setRequestedTimeRange } = useRequestedTimeRange(INITIAL)
    await nextTick()

    setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()

    const published = useGlobalTimeRange().activeTimeRange.value
    expect(published).not.toBeNull()
    expect(epochSeconds(published!.from)).toBe(5_000)
    expect(epochSeconds(published!.to)).toBe(6_000)
  })

  test('reuses the active range timezone when publishing a local update', async () => {
    useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')
    const { setRequestedTimeRange } = useRequestedTimeRange(INITIAL)
    await nextTick()

    setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()

    const published = useGlobalTimeRange().activeTimeRange.value
    expect(published!.from.timeZone).toBe(TZ)
    expect(published!.to.timeZone).toBe(TZ)
  })

  test('falls back to the local timezone when publishing without a prior picker range', async () => {
    const { setRequestedTimeRange } = useRequestedTimeRange(INITIAL)

    setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()

    const published = useGlobalTimeRange().activeTimeRange.value
    expect(published!.from.timeZone).toBe(getLocalTimeZone())
  })

  test('propagates a local update to another consumer sharing the same picker', async () => {
    const first = useRequestedTimeRange(INITIAL)
    const second = useRequestedTimeRange(INITIAL)
    await nextTick()

    first.setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()

    expect(second.requestedTimeRange.value).toEqual({ start: 5_000, end: 6_000 })
  })

  test('settles instead of bouncing indefinitely once a local update round-trips back', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { requestedTimeRange, setRequestedTimeRange } = useRequestedTimeRange(INITIAL)

    setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()
    await nextTick()
    await nextTick()

    expect(requestedTimeRange.value).toEqual({ start: 5_000, end: 6_000 })
    expect(errorSpy).not.toHaveBeenCalled()
    errorSpy.mockRestore()
  })

  describe('counting the windows a time control asked for', () => {
    test('starts at nothing asked for', () => {
      const { timePickerRequests } = useRequestedTimeRange(INITIAL)

      expect(timePickerRequests.value).toBe(0)
    })

    test('a picker range counts', async () => {
      const { timePickerRequests } = useRequestedTimeRange(INITIAL)

      useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'time_picker')
      await nextTick()

      expect(timePickerRequests.value).toBe(1)
    })

    test('an external range does not count, however far it moves the window', async () => {
      const { timePickerRequests } = useRequestedTimeRange(INITIAL)

      useGlobalTimeRange().setActiveTimeRange(range(9, 10), 'external')
      await nextTick()

      expect(timePickerRequests.value).toBe(0)
    })

    test('the picker republishing the window already shown does not count', async () => {
      const published = range(9, 10)
      useGlobalTimeRange().setActiveTimeRange(published, 'time_picker')
      const { timePickerRequests } = useRequestedTimeRange(INITIAL)
      await nextTick()

      useGlobalTimeRange().setActiveTimeRange(published, 'time_picker')
      await nextTick()

      expect(timePickerRequests.value).toBe(0)
    })

    test("this owner's own write does not count, even once it round-trips back", async () => {
      const { setRequestedTimeRange, timePickerRequests } = useRequestedTimeRange(INITIAL)

      setRequestedTimeRange({ start: 5_000, end: 6_000 })
      await nextTick()
      await nextTick()

      expect(timePickerRequests.value).toBe(0)
    })
  })
})
