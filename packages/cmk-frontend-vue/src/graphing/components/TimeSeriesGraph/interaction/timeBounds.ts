/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeRange } from '../types'

/**
 * The far end of the navigable time axis: 23:59:59 of the current day in the browser's zone.
 * The calendar quick ranges ("Today") end there too, so panning and the time picker agree on
 * how far into the future a graph may look.
 */
export function endOfCurrentDaySeconds(now: Date = new Date()): number {
  const endOfDay = new Date(now)
  endOfDay.setHours(23, 59, 59, 999)
  return Math.floor(endOfDay.getTime() / 1000)
}

/** Slides a range back so it ends no later than `latestEnd`, keeping its span. */
export function withinNavigableTime(range: TimeRange, latestEnd: number): TimeRange {
  const overshoot = range.end - latestEnd
  if (overshoot <= 0) {
    return range
  }
  return { ...range, start: range.start - overshoot, end: latestEnd }
}
