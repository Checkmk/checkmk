/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate, getLocalTimeZone, today } from '@internationalized/date'

import type { Weekday } from '../../types'

/** A calendar date's weekday (0=Sunday … 6=Saturday), timezone-free: create and read the instant in
 * the same fixed zone (UTC) so it never shifts. `getUTCDay()` is by definition in 0..6. */
export function weekdayOf(date: CalendarDate): Weekday {
  return date.toDate('UTC').getUTCDay() as Weekday
}

/**
 * Target date for a grid navigation key, or `null` if `key` isn't a navigation key (e.g. Enter,
 * Space). Arrows move by a day (Left/Right) or a week (Up/Down); Home/End jump to the first/last day
 * of `from`'s week (anchored on `firstDayOfWeek`); PageUp/PageDown step one month, or one year when
 * `shift` is held. The month/year steps clamp the day into the target month (e.g. Jan 31 → Feb 28),
 * matching the APG "matching day number or last day if unavailable" rule.
 */
export function navTarget(
  key: string,
  shift: boolean,
  from: CalendarDate,
  firstDayOfWeek: Weekday
): CalendarDate | null {
  const intoWeek = (weekdayOf(from) - firstDayOfWeek + 7) % 7
  switch (key) {
    case 'ArrowLeft':
      return from.subtract({ days: 1 })
    case 'ArrowRight':
      return from.add({ days: 1 })
    case 'ArrowUp':
      return from.subtract({ days: 7 })
    case 'ArrowDown':
      return from.add({ days: 7 })
    case 'Home':
      return from.subtract({ days: intoWeek })
    case 'End':
      return from.add({ days: 6 - intoWeek })
    case 'PageUp':
      return from.subtract(shift ? { years: 1 } : { months: 1 })
    case 'PageDown':
      return from.add(shift ? { years: 1 } : { months: 1 })
    default:
      return null
  }
}

/** A whole-month ordinal (`year * 12 + monthIndex`) for calendar-independent month arithmetic. */
export function monthIndex(date: CalendarDate): number {
  return date.year * 12 + (date.month - 1)
}

/** Inverse of {@link monthIndex}; the returned date is the first of that month. */
export function monthFromIndex(index: number): CalendarDate {
  return new CalendarDate(Math.floor(index / 12), (index % 12) + 1, 1)
}

/** How far the year dropdown reaches back from the reference year by default. */
export const DEFAULT_YEARS_PAST = 20
/** How far the year dropdown reaches into the future from the reference year by default. */
export const DEFAULT_YEARS_FUTURE = 2

/**
 * The default `[from, to]` span offered by the year dropdown: {@link DEFAULT_YEARS_PAST} years back
 * and {@link DEFAULT_YEARS_FUTURE} years ahead of `referenceYear` (today's year by default). Years
 * outside this span remain reachable via the prev/next buttons or by typing into the date field.
 */
export function defaultYearRange(
  referenceYear: number = today(getLocalTimeZone()).year
): [number, number] {
  return [referenceYear - DEFAULT_YEARS_PAST, referenceYear + DEFAULT_YEARS_FUTURE]
}
