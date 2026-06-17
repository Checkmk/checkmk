/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type CalendarDate,
  CalendarDateTime,
  DateFormatter,
  type ZonedDateTime,
  toCalendarDate,
  toTimeZone,
  toZoned
} from '@internationalized/date'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type {
  DateFormatParts,
  DateTimeParts,
  DateTimePartsDraft,
  HourCycle,
  Meridiem,
  MeridiemCycle,
  RangeDraft,
  TimeValue
} from './types'

/** A concrete default time for selectors that need a complete wall clock. */
export const MIDNIGHT: TimeValue = { hour: 0, minute: 0 }

/** Whether a date-time draft already forms a complete wall clock. */
export function isDateTimeParts(value: DateTimePartsDraft): value is DateTimeParts {
  return value.date !== null && value.time !== null
}

/** Whether a date-time draft is fully empty. */
export function isEmptyDateTimePartsDraft(value: DateTimePartsDraft): boolean {
  return value.date === null && value.time === null
}

/** Convert a canonical 0-23 hour to the display parts for a meridiem cycle: the displayed hour plus
 * its AM/PM marker. h12 shows the noon/midnight slot as `12`, h11 as `0`. */
export function toMeridiemHour(
  hour: number,
  cycle: MeridiemCycle
): { displayHour: number; meridiem: Meridiem } {
  if (hour < 0 || hour > 23) {
    throw new RangeError(`hour must be in 0..23, got ${hour}`)
  }
  const meridiem: Meridiem = hour < 12 ? 'AM' : 'PM'
  const mod = hour % 12 // 0..11
  const displayHour = cycle === 11 ? mod : mod === 0 ? 12 : mod
  return { displayHour, meridiem }
}

/** Convert meridiem display parts back to a canonical 0-23 hour. The arithmetic is the same for
 * both cycles (`displayHour % 12`), so no cycle is needed: an h12 `12` and an h11 `0` both map to
 * the same canonical hour. */
export function fromMeridiemHour(displayHour: number, meridiem: Meridiem): number {
  if (displayHour < 0 || displayHour > 12) {
    throw new RangeError(`displayHour must be in 0..12, got ${displayHour}`)
  }
  const base = displayHour % 12 // h12: 12 -> 0; h11: 0..11 unchanged
  return meridiem === 'PM' ? base + 12 : base
}

/** Format a date for read-only display, following the resolved section order and separator. */
export function formatDate(date: CalendarDate, format: DateFormatParts): string {
  return format.order
    .map((section) => {
      const value = section === 'year' ? date.year : section === 'month' ? date.month : date.day
      return value.toString().padStart(section === 'year' ? 4 : 2, '0')
    })
    .join(format.separator)
}

/** Format a clock time for read-only display in the resolved hour cycle (e.g. `08:45 PM`). */
export function formatTime(time: TimeValue, hourCycle: HourCycle): string {
  const minute = time.minute.toString().padStart(2, '0')
  if (hourCycle === 24) {
    return `${time.hour.toString().padStart(2, '0')}:${minute}`
  }
  const { displayHour, meridiem } = toMeridiemHour(time.hour, hourCycle)
  return `${displayHour.toString().padStart(2, '0')}:${minute} ${meridiem}`
}

/** Locale-bound "month year" formatter, e.g. en-US `"June 2026"`. */
export function makeMonthYearFormatter(locale: string): (date: CalendarDate) => TranslatedString {
  const formatter = new DateFormatter(locale, { year: 'numeric', month: 'long', timeZone: 'UTC' })
  return (date) => untranslated(formatter.format(date.toDate('UTC')))
}

/** Locale-bound long-date formatter without the weekday, e.g. en-US `"June 10, 2026"`. */
export function makeLongDateFormatter(locale: string): (date: CalendarDate) => TranslatedString {
  const formatter = new DateFormatter(locale, { dateStyle: 'long', timeZone: 'UTC' })
  return (date) => untranslated(formatter.format(date.toDate('UTC')))
}

function timeZoneNamePart(
  timeZone: string,
  at: Date,
  style: 'short' | 'shortOffset',
  locale: string
): string {
  const formatter = new DateFormatter(locale, { timeZone, timeZoneName: style })
  return formatter.formatToParts(at).find((part) => part.type === 'timeZoneName')?.value ?? ''
}

/** Find an English abbreviation for the zone (e.g. `CEST`, `PDT`, `IST`). CLDR only carries
 * abbreviations in the locales that use them, so probe a few English locales and take the first
 * real (non-`GMT±h`) one. Returns '' for zones that have no English abbreviation at all. */
function timeZoneAbbreviation(timeZone: string, at: Date): string {
  for (const locale of ['en-US', 'en-GB', 'en-IN', 'en-AU']) {
    const name = timeZoneNamePart(timeZone, at, 'short', locale)
    if (name && !/^(GMT|UTC)/.test(name)) {
      return name
    }
  }
  return ''
}

/**
 * Compact timezone label like `CEST (UTC+2)`: the English abbreviation plus the UTC offset, both
 * at the given instant (offsets are DST-dependent). Zones without an abbreviation render as just
 * the offset (e.g. `UTC+9`), and a zero offset as just `UTC`.
 */
export function timeZoneShortLabel(timeZone: string, at: Date): string {
  const offset =
    timeZoneNamePart(timeZone, at, 'shortOffset', 'en-US').replace(/^GMT/, 'UTC') || 'UTC'
  const abbreviation = timeZoneAbbreviation(timeZone, at)
  return abbreviation ? `${abbreviation} (${offset})` : offset
}

/** Human-friendly rendering of an IANA timezone id: `Europe/Berlin` → `Europe, Berlin`. An empty
 *  id (no resolvable zone) renders as a translated fallback. */
export function timeZoneRegionLabel(timeZone: string): string {
  if (timeZone === '') {
    return usei18n()._t('Unknown Timezone')
  }
  return timeZone.replaceAll('_', ' ').replaceAll('/', ', ')
}

/** Split a `ZonedDateTime` into the timezone-free wall-clock parts the pickers edit. */
export function zonedToParts(zoned: ZonedDateTime): { date: CalendarDate; time: TimeValue } {
  return {
    date: toCalendarDate(zoned),
    time: { hour: zoned.hour, minute: zoned.minute }
  }
}

/**
 * Combine wall-clock parts, interpreted in `timeZone`, into a `ZonedDateTime` instant.
 *
 * When `current` already spells the same wall clock (minute granularity, compared in
 * `timeZone`), it is returned unchanged — a no-op Apply never rewrites the model, so an
 * instant in the ambiguous fall-back hour never shifts. Edited parts are resolved with the
 * explicit `'compatible'` disambiguation: times in the spring-forward gap move forward,
 * ambiguous fall-back times take the earlier offset.
 */
export function partsToZoned(
  date: CalendarDate,
  time: TimeValue,
  timeZone: string,
  current: ZonedDateTime | null
): ZonedDateTime {
  if (current !== null) {
    const base = toTimeZone(current, timeZone)
    if (
      base.year === date.year &&
      base.month === date.month &&
      base.day === date.day &&
      base.hour === time.hour &&
      base.minute === time.minute
    ) {
      return current
    }
  }
  return toZoned(
    new CalendarDateTime(date.year, date.month, date.day, time.hour, time.minute),
    timeZone,
    'compatible'
  )
}

/**
 * Decompose a stored instant into the wall-clock parts the pickers edit, read in `timeZone`.
 * `null` (an empty endpoint) passes straight through to empty parts. This is the nullable,
 * timezone-normalizing counterpart to {@link zonedToParts}.
 */
export function instantToParts(value: ZonedDateTime | null, timeZone: string): DateTimePartsDraft {
  return value ? zonedToParts(toTimeZone(value, timeZone)) : { date: null, time: null }
}

/**
 * Recompose complete wall-clock parts into an instant in `timeZone`.
 * Delegates to {@link partsToZoned}, so `current` is preserved when the parts weren't edited: a
 * no-op Apply never rewrites the model (and never shifts a value in the ambiguous fall-back hour).
 */
export function partsToInstant(
  parts: DateTimeParts,
  timeZone: string,
  current: ZonedDateTime | null
): ZonedDateTime {
  return partsToZoned(parts.date, parts.time, timeZone, current)
}

/** A wall-clock time as minutes since midnight. */
function minutesOfDay(time: TimeValue): number {
  const { hour, minute } = time
  return hour * 60 + minute
}

/**
 * Whether a staged range is inverted (`from` strictly after `to`) by wall-clock comparison — date
 * first, then time-of-day. An incomplete range (missing a date or time) is never inverted, so
 * callers can ask unconditionally. Wall-clock (not instant) comparison
 * matches what the user reads on screen and is intentionally indifferent to the DST fall-back hour.
 */
export function isRangeInverted(draft: RangeDraft): boolean {
  const { from, to } = draft
  if (!isDateTimeParts(from) || !isDateTimeParts(to)) {
    return false
  }
  const dateOrder = from.date.compare(to.date)
  return dateOrder !== 0 ? dateOrder > 0 : minutesOfDay(from.time) > minutesOfDay(to.time)
}

/** Exchange a range's two endpoints (`from` ↔ `to`), carrying each endpoint's parts unchanged. The
 *  operation is involutive: swapping twice restores the original draft. */
export function swapRangeEndpoints(draft: RangeDraft): RangeDraft {
  return { from: draft.to, to: draft.from }
}
