/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  endOfCurrentDaySeconds,
  withinNavigableTime
} from '@/graphing/components/TimeSeriesGraph/interaction/timeBounds'

describe('endOfCurrentDaySeconds', () => {
  test('is the last second of the given day', () => {
    const middleOfTheDay = new Date(2026, 7, 5, 14, 30, 0)

    const bound = endOfCurrentDaySeconds(middleOfTheDay)

    expect(new Date(bound * 1000)).toEqual(new Date(2026, 7, 5, 23, 59, 59))
  })

  test('does not reach into the next day', () => {
    const justBeforeMidnight = new Date(2026, 7, 5, 23, 59, 58)

    const bound = endOfCurrentDaySeconds(justBeforeMidnight)

    expect(new Date(bound * 1000).getDate()).toBe(5)
  })
})

describe('withinNavigableTime', () => {
  const bounds = { earliestStart: 0, latestEnd: 1000 }

  test('slides a range that overshoots the bound back, keeping its span', () => {
    const pannedIntoTheFuture = { start: 900, end: 1200, step: 60 }

    const bounded = withinNavigableTime(pannedIntoTheFuture, bounds)

    expect(bounded).toEqual({ start: 700, end: 1000, step: 60 })
  })

  test('leaves a range that ends before the bound untouched', () => {
    const range = { start: 400, end: 700, step: 60 }

    const bounded = withinNavigableTime(range, bounds)

    expect(bounded).toEqual(range)
  })

  test('leaves a range ending exactly on the bound untouched', () => {
    const range = { start: 700, end: 1000, step: 60 }

    const bounded = withinNavigableTime(range, bounds)

    expect(bounded).toEqual(range)
  })
})
