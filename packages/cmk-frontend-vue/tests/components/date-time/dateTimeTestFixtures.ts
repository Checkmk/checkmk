/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { makeLongDateFormatter, makeMonthYearFormatter } from '@/components/date-time/dateTimeUtils'
import type { ResolvedDateTimeSettings, WeekdayNames } from '@/components/date-time/types'
import type { DateFormatParts } from '@/components/date-time/types'

export const TZ_UTC = 'UTC'
export const TZ_BERLIN = 'Europe/Berlin'
export const TZ_TOKYO = 'Asia/Tokyo'

/** Day-month-year order, dot-separated (e.g. German). */
export const DMY: DateFormatParts = { order: ['day', 'month', 'year'], separator: '.' }
/** Year-month-day order, dash-separated (ISO 8601 style). */
export const YMD: DateFormatParts = { order: ['year', 'month', 'day'], separator: '-' }

export const MONTH_NAMES_EN: TranslatedString[] = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December'
].map(untranslated)

export const WEEKDAY_NAMES_NARROW_EN: WeekdayNames = {
  0: untranslated('S'),
  1: untranslated('M'),
  2: untranslated('T'),
  3: untranslated('W'),
  4: untranslated('T'),
  5: untranslated('F'),
  6: untranslated('S')
}

export const WEEKDAY_NAMES_SHORT_EN: WeekdayNames = {
  0: untranslated('Sun'),
  1: untranslated('Mon'),
  2: untranslated('Tue'),
  3: untranslated('Wed'),
  4: untranslated('Thu'),
  5: untranslated('Fri'),
  6: untranslated('Sat')
}

export const WEEKDAY_NAMES_LONG_EN: WeekdayNames = {
  0: untranslated('Sunday'),
  1: untranslated('Monday'),
  2: untranslated('Tuesday'),
  3: untranslated('Wednesday'),
  4: untranslated('Thursday'),
  5: untranslated('Friday'),
  6: untranslated('Saturday')
}

export const MONTH_NAMES_SHORT_EN: TranslatedString[] = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec'
].map(untranslated)

/**
 * A complete, deterministic {@link ResolvedDateTimeSettings} for tests, composed from the EN
 * fixtures above and `'en-US'`-bound formatters (so spoken strings don't depend on the test env's
 * `navigator.language`). Typed as `ResolvedDateTimeSettings` so the compiler flags any drift if the
 * interface gains a field. Pass `overrides` to tweak individual values per test.
 */
export function makeSettings(
  overrides: Partial<ResolvedDateTimeSettings> = {}
): ResolvedDateTimeSettings {
  return {
    hourCycle: 24,
    firstDayOfWeek: 0,
    weekendDays: [0, 6],
    dateFormat: DMY,
    monthNamesShort: MONTH_NAMES_SHORT_EN,
    monthNamesLong: MONTH_NAMES_EN,
    weekdayNamesNarrow: WEEKDAY_NAMES_NARROW_EN,
    weekdayNamesShort: WEEKDAY_NAMES_SHORT_EN,
    weekdayNamesLong: WEEKDAY_NAMES_LONG_EN,
    timeZone: TZ_UTC,
    formatMonthYear: makeMonthYearFormatter('en-US'),
    formatLongDate: makeLongDateFormatter('en-US'),
    ...overrides
  }
}
