/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  CalendarDate,
  DateFormatter,
  getLocalTimeZone,
  isWeekend,
  startOfWeek
} from '@internationalized/date'
import { type MaybeRefOrGetter, computed, reactive, toValue } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { makeLongDateFormatter, makeMonthYearFormatter } from './dateTimeUtils'
import type {
  DateFormatKind,
  DateFormatParts,
  DateSectionType,
  DateTimeSettings,
  HourCycle,
  MonthNameStyle,
  ResolvedDateTimeSettings,
  Weekday,
  WeekdayNameStyle,
  WeekdayNames
} from './types'

/** The browser locale, with a stable fallback for non-browser (test) environments. */
function currentLocale(): string {
  if (typeof navigator !== 'undefined' && navigator.language) {
    return navigator.language
  }
  return 'en-US'
}

/** Resolve the display cycle from the locale, honoring an explicit override. The locale's
 * `hourCycle` is the only signal that distinguishes h11 from h12 (`hour12` cannot), so it is
 * preferred; an absent cycle (very old engines) falls back to 24-hour. */
function resolveHourCycle(explicit?: HourCycle): HourCycle {
  if (explicit !== undefined) {
    return explicit
  }
  const { hourCycle } = new DateFormatter(currentLocale(), {
    hour: 'numeric'
  }).resolvedOptions()
  if (hourCycle === 'h11') {
    return 11
  }
  if (hourCycle === 'h12') {
    return 12
  }
  return 24 // 'h23', 'h24', or absent
}

/** Resolve the first day of the week (0=Sunday … 6=Saturday), honoring an explicit override. */
function resolveFirstDayOfWeek(explicit: Weekday | undefined): Weekday {
  if (explicit !== undefined) {
    return explicit
  }
  const reference = new CalendarDate(2024, 1, 7) // a Sunday
  const weekStart = startOfWeek(reference, currentLocale())
  // A calendar date's weekday is timezone-free; create and read the instant in the same fixed
  // zone (UTC) so it never shifts. getUTCDay() is by definition in 0..6.
  return weekStart.toDate('UTC').getUTCDay() as Weekday
}

/** Resolve weekend days (0=Sunday … 6=Saturday), honoring an explicit override and otherwise
 * deriving from the locale. */
function resolveWeekendDays(explicit: Weekday[] | undefined): Weekday[] {
  if (explicit !== undefined) {
    return explicit
  }
  const locale = currentLocale()
  const sunday = new CalendarDate(2024, 1, 7) // a Sunday
  const days: Weekday[] = []
  // Iterating Sunday → Saturday yields the result already in ascending 0..6 order. Read each
  // weekday timezone-free via UTC, mirroring resolveFirstDayOfWeek.
  for (let offset = 0; offset < 7; offset++) {
    const date = sunday.add({ days: offset })
    if (isWeekend(date, locale)) {
      days.push(date.toDate('UTC').getUTCDay() as Weekday)
    }
  }
  return days
}

/** Resolve the date section order + separator from the locale, or fixed ISO `YYYY-MM-DD`. */
function resolveDateFormat(kind: DateFormatKind): DateFormatParts {
  if (kind === 'iso') {
    return { order: ['year', 'month', 'day'], separator: '-' }
  }
  const formatter = new DateFormatter(currentLocale(), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
  const order: DateSectionType[] = []
  let separator = ''
  for (const part of formatter.formatToParts(new Date(2026, 2, 20))) {
    if (part.type === 'year') {
      order.push('year')
    } else if (part.type === 'month') {
      order.push('month')
    } else if (part.type === 'day') {
      order.push('day')
    } else if (part.type === 'literal' && !separator && part.value.trim()) {
      separator = part.value.trim()
    }
  }
  if (order.length !== 3) {
    return { order: ['year', 'month', 'day'], separator: '-' }
  }
  return { order, separator: separator || '-' }
}

/** Localized month names (index 0 = January). Locale-only; created and formatted in UTC so the
 * instant's calendar day can never shift between creation and formatting. */
function monthNames(style: MonthNameStyle): TranslatedString[] {
  const formatter = new DateFormatter(currentLocale(), { month: style, timeZone: 'UTC' })
  return Array.from({ length: 12 }, (_unused, index) =>
    untranslated(formatter.format(new CalendarDate(2024, index + 1, 1).toDate('UTC')))
  )
}

/** Localized weekday names keyed by absolute weekday (0=Sunday … 6=Saturday). Locale-only; see
 * {@link monthNames} for why creation and formatting both use UTC. */
function weekdayNames(style: WeekdayNameStyle): WeekdayNames {
  const formatter = new DateFormatter(currentLocale(), { weekday: style, timeZone: 'UTC' })
  const sunday = new CalendarDate(2024, 1, 7) // a Sunday
  const nameFor = (day: Weekday): TranslatedString =>
    untranslated(formatter.format(sunday.add({ days: day }).toDate('UTC')))
  return {
    0: nameFor(0),
    1: nameFor(1),
    2: nameFor(2),
    3: nameFor(3),
    4: nameFor(4),
    5: nameFor(5),
    6: nameFor(6)
  }
}

export function useResolvedDateTimeSettings(
  settings?: MaybeRefOrGetter<Partial<DateTimeSettings> | undefined>,
  timeZone?: MaybeRefOrGetter<string | undefined>
): ResolvedDateTimeSettings {
  // The timezone is a pure passthrough (instant conversion, calendar "today"); none of the
  // locale-derived display settings depend on it.
  const resolvedTimeZone = computed(() => toValue(timeZone) ?? getLocalTimeZone())
  return reactive({
    hourCycle: computed(() => resolveHourCycle(toValue(settings)?.hourCycle)),
    firstDayOfWeek: computed(() => resolveFirstDayOfWeek(toValue(settings)?.firstDayOfWeek)),
    weekendDays: computed(() => resolveWeekendDays(toValue(settings)?.weekendDays)),
    dateFormat: computed(() => resolveDateFormat(toValue(settings)?.dateFormat ?? 'locale')),
    monthNamesShort: computed(() => monthNames('short')),
    monthNamesLong: computed(() => monthNames('long')),
    weekdayNamesNarrow: computed(() => weekdayNames('narrow')),
    weekdayNamesShort: computed(() => weekdayNames('short')),
    weekdayNamesLong: computed(() => weekdayNames('long')),
    timeZone: resolvedTimeZone,
    formatMonthYear: computed(() => makeMonthYearFormatter(currentLocale())),
    formatLongDate: computed(() => makeLongDateFormatter(currentLocale()))
  })
}
