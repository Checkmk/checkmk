/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { nextTick } from 'vue'

import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/globalTimeState'
import { useLocalTimeRange } from '@/graphing/composables/useLocalTimeRange'

const TZ = 'Europe/Berlin'
const zoned = (day: number): ZonedDateTime =>
  toZoned(new CalendarDateTime(2026, 3, day, 0, 0), TZ, 'compatible')
const pickerRange = (fromDay: number, toDay: number): DateTimeRange => ({
  from: zoned(fromDay),
  to: zoned(toDay)
})

const INITIAL = { start: 1_000, end: 2_000 }

describe('useLocalTimeRange', () => {
  // The global picker store is a module-level singleton shared across the whole bundle; reset it
  // so each test starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
  })

  test('starts at the range it was seeded with', () => {
    expect(useLocalTimeRange(INITIAL).requestedTimeRange.value).toEqual(INITIAL)
  })

  test('a range the owner sets stays off the page-global picker', async () => {
    const { setRequestedTimeRange, requestedTimeRange } = useLocalTimeRange(INITIAL)

    setRequestedTimeRange({ start: 5_000, end: 6_000 })
    await nextTick()

    expect(requestedTimeRange.value).toEqual({ start: 5_000, end: 6_000 })
    expect(useGlobalTimeRange().activeTimeRange.value).toBeNull()
  })

  test('a range the page-global picker publishes leaves the owner alone', async () => {
    const { requestedTimeRange } = useLocalTimeRange(INITIAL)

    useGlobalTimeRange().setActiveTimeRange(pickerRange(1, 2), 'time_picker')
    await nextTick()

    expect(requestedTimeRange.value).toEqual(INITIAL)
  })

  test('the owner is seeded even while the picker already holds a range', () => {
    useGlobalTimeRange().setActiveTimeRange(pickerRange(1, 2), 'time_picker')

    expect(useLocalTimeRange(INITIAL).requestedTimeRange.value).toEqual(INITIAL)
  })
})
