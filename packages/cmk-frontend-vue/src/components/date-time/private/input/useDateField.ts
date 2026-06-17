/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { type ComputedRef, type MaybeRefOrGetter, computed, toValue } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { DateFormatParts, DateSectionType } from '../../types'
import {
  type FieldType,
  type SegmentText,
  clampToRange,
  digitsAreComplete,
  padNumber,
  parseSegment,
  wrapToRange
} from './useSegmentedField'

const DATE_RANGES: Record<DateSectionType, [number, number]> = {
  day: [1, 31],
  month: [1, 12],
  year: [1, 9999]
}

const PAD: Record<DateSectionType, number> = { day: 2, month: 2, year: 4 }

/** The segments as a date, or `null` while incomplete or impossible (e.g. Feb 30). */
function dateToValue(text: SegmentText): CalendarDate | null {
  const day = parseSegment(text.day ?? '')
  const month = parseSegment(text.month ?? '')
  const year = parseSegment(text.year ?? '')
  if (day === null || month === null || year === null) {
    return null
  }
  const candidate = new CalendarDate(year, month, day)
  // Reject impossible dates, which CalendarDate would otherwise normalize.
  if (candidate.day !== day || candidate.month !== month) {
    return null
  }
  return candidate
}

/** Number of days in the given month/year (the day's true ceiling once both are known). */
function maxDayInMonth(month: number, year: number): number {
  const reference = new CalendarDate(year, month, 1)
  return reference.calendar.getDaysInMonth(reference)
}

/** Pad each non-empty segment into range and snap the day to its month once the date is complete. */
function normalizeDate(text: SegmentText): SegmentText {
  const next: SegmentText = { ...text }
  for (const section of ['day', 'month', 'year'] as DateSectionType[]) {
    const value = parseSegment(next[section] ?? '')
    if (value !== null) {
      const [min, max] = DATE_RANGES[section]
      next[section] = padNumber(clampToRange(value, min, max), PAD[section])
    }
  }
  const day = parseSegment(next.day ?? '')
  const month = parseSegment(next.month ?? '')
  const year = parseSegment(next.year ?? '')
  if (day !== null && month !== null && year !== null) {
    const max = maxDayInMonth(month, year)
    if (day > max) {
      next.day = padNumber(max, 2)
    }
  }
  return next
}

function stepDate(text: SegmentText, key: string, delta: 1 | -1): { text: SegmentText } {
  const section = key as DateSectionType
  const date = dateToValue(text)
  if (date !== null) {
    // Complete date: real calendar arithmetic (handles month rollovers and end-of-month
    // clamping, e.g. Jan 31 +1 month → Feb 28).
    const next = date.add(
      section === 'day'
        ? { days: delta }
        : section === 'month'
          ? { months: delta }
          : { years: delta }
    )
    return {
      text: {
        ...text,
        day: padNumber(next.day, 2),
        month: padNumber(next.month, 2),
        year: padNumber(next.year, 4)
      }
    }
  }
  // Incomplete or impossible date: step just this part (the year clamps, day/month wrap).
  const [min, max] = DATE_RANGES[section]
  const current = parseSegment(text[section] ?? '')
  const value =
    current === null
      ? min
      : section === 'year'
        ? clampToRange(current + delta, min, max)
        : wrapToRange(current + delta, min, max)
  return { text: { ...text, [section]: padNumber(value, PAD[section]) } }
}

function makeDateField(
  format: DateFormatParts,
  monthNamesLong: TranslatedString[],
  labels: Record<DateSectionType, TranslatedString>
): FieldType<CalendarDate> {
  return {
    segments: format.order.map((section) => ({
      key: section,
      ariaLabel: labels[section],
      widthCh: PAD[section],
      pad: PAD[section],
      placeholder: '-'.repeat(PAD[section]),
      options: [],
      // The month reads as its name, e.g. "June"
      ...(section === 'month'
        ? {
            valueText: (text: string): TranslatedString | undefined => {
              const month = parseSegment(text)
              return month !== null && month >= 1 && month <= 12
                ? monthNamesLong[month - 1]
                : undefined
            }
          }
        : {})
    })),
    separator: format.separator,
    // The day's max follows the entered month/year (Feb 2026 → 28), else the absolute 31.
    bounds: (key, text) => {
      const section = key as DateSectionType
      if (section === 'day') {
        const month = parseSegment(text.month ?? '')
        const year = parseSegment(text.year ?? '')
        const known = month !== null && month >= 1 && month <= 12 && year !== null && year >= 1
        return {
          min: DATE_RANGES.day[0],
          max: known ? maxDayInMonth(month, year) : DATE_RANGES.day[1]
        }
      }
      const [min, max] = DATE_RANGES[section]
      return { min, max }
    },
    toText: (date) =>
      date === null
        ? { day: '', month: '', year: '' }
        : {
            day: padNumber(date.day, 2),
            month: padNumber(date.month, 2),
            year: padNumber(date.year, 4)
          },
    toValue: dateToValue,
    normalize: normalizeDate,
    step: stepDate,
    isComplete: (key, digits) =>
      digitsAreComplete(
        digits,
        PAD[key as DateSectionType],
        DATE_RANGES[key as DateSectionType][1]
      ),
    typeChar: () => undefined
  }
}

/** Reactive date {@link FieldType} for a `<SegmentedField>`. */
export function useDateField(
  format: MaybeRefOrGetter<DateFormatParts>,
  monthNames: MaybeRefOrGetter<TranslatedString[]>
): ComputedRef<FieldType<CalendarDate>> {
  const { _t } = usei18n()
  const labels: Record<DateSectionType, TranslatedString> = {
    day: _t('Day'),
    month: _t('Month'),
    year: _t('Year')
  }
  return computed(() => makeDateField(toValue(format), toValue(monthNames), labels))
}
