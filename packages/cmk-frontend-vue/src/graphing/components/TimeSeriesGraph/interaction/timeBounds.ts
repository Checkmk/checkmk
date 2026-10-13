/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeInterval } from '../../../types'

const EARLIEST_NAVIGABLE_YEAR = 2008

/** The near end of the navigable time axis: the first second of 2008 in the browser's zone. */
export const EARLIEST_NAVIGABLE_SECONDS = Math.floor(
  new Date(EARLIEST_NAVIGABLE_YEAR, 0, 1).getTime() / 1000
)

/** The ends of the navigable time axis, in unix seconds. */
export interface NavigableBounds {
  earliestStart: number
  latestEnd: number
}

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

export function navigableBounds(now: Date = new Date()): NavigableBounds {
  return { earliestStart: EARLIEST_NAVIGABLE_SECONDS, latestEnd: endOfCurrentDaySeconds(now) }
}

/**
 * Slides a range onto the navigable axis, keeping its span: a window taken past either end
 * comes to rest against that end. A span wider than the whole axis cannot keep it and is
 * trimmed to the axis instead.
 */
export function withinNavigableTime<Interval extends TimeInterval>(
  interval: Interval,
  bounds: NavigableBounds
): Interval {
  const pastLatestEnd = Math.max(0, interval.end - bounds.latestEnd)
  const beforeEarliestStart = Math.max(0, bounds.earliestStart - (interval.start - pastLatestEnd))
  const shiftSeconds = beforeEarliestStart - pastLatestEnd
  if (shiftSeconds === 0) {
    return interval
  }
  return {
    ...interval,
    start: Math.max(bounds.earliestStart, interval.start + shiftSeconds),
    end: Math.min(bounds.latestEnd, interval.end + shiftSeconds)
  }
}

export function clippedToNavigableTime<Interval extends TimeInterval>(
  interval: Interval,
  bounds: NavigableBounds
): Interval {
  return {
    ...interval,
    start: Math.max(interval.start, bounds.earliestStart),
    end: Math.min(interval.end, bounds.latestEnd)
  }
}
