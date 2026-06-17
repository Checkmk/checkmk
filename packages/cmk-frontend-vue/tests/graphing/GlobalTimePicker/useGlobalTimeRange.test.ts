/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { beforeEach, describe, expect, test } from 'vitest'
import { nextTick, watch } from 'vue'

import type { DateTimeRange } from '@/components/date-time'

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
})
