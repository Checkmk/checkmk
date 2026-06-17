/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type MaybeRefOrGetter, computed, toValue } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { fromMeridiemHour, toMeridiemHour } from '../../dateTimeUtils'
import type { HourCycle, Meridiem, MeridiemCycle, TimeValue } from '../../types'
import {
  type FieldType,
  type Segment,
  type SegmentText,
  clampToRange,
  digitsAreComplete,
  padNumber,
  parseSegment,
  wrapToRange
} from './useSegmentedField'

interface TimeLabels {
  hours: TranslatedString
  minutes: TranslatedString
  meridiem: TranslatedString
}

const MERIDIEMS: Meridiem[] = ['AM', 'PM']

/** The meridiem the segments currently show, defaulting to `AM` while none is set. */
function displayedMeridiem(text: SegmentText): Meridiem {
  return (text.meridiem as Meridiem) ?? 'AM'
}

/** Whether `value` is a hour the meridiem cycle displays directly (h12: `1..12`, h11: `0..11`); if
 * not, it is a 24h-style value to be reinterpreted into the cycle. */
function isDisplayHour(value: number, cycle: MeridiemCycle): boolean {
  return cycle === 12 ? value >= 1 && value <= 12 : value >= 0 && value <= 11
}

/** The canonical 0-23 hour the segments currently spell, or `null` while the hour is empty. A
 * `null` cycle is the 24-hour mode, where the displayed hour is already canonical. */
function canonicalHour(text: SegmentText, cycle: MeridiemCycle | null): number | null {
  const hour = parseSegment(text.hour ?? '')
  if (hour === null) {
    return null
  }
  return cycle !== null ? fromMeridiemHour(hour, displayedMeridiem(text)) : hour
}

/** Write a canonical 0-23 hour back as display segments (the displayed hour plus its meridiem). */
function putHour(text: SegmentText, hour: number, cycle: MeridiemCycle | null): SegmentText {
  if (cycle === null) {
    return { ...text, hour: padNumber(hour, 2) }
  }
  const { displayHour, meridiem } = toMeridiemHour(hour, cycle)
  return { ...text, hour: padNumber(displayHour, 2), meridiem }
}

/**
 * Pad the segments for display. In a meridiem cycle a typed value outside the cycle's displayed
 * range is a 24h-style value that pins the meridiem (h12: 00 → 12 AM, 13-23 → their natural PM;
 * h11: 12 → 0 PM, 13-23 → their natural PM); an in-range hour keeps the displayed meridiem.
 */
function normalizeTime(text: SegmentText, cycle: MeridiemCycle | null): SegmentText {
  const next: SegmentText = { ...text }
  const hour = parseSegment(next.hour ?? '')
  if (hour !== null) {
    const typed = clampToRange(hour, 0, 23)
    if (cycle !== null && !isDisplayHour(typed, cycle)) {
      const display = toMeridiemHour(typed, cycle)
      next.hour = padNumber(display.displayHour, 2)
      next.meridiem = display.meridiem
    } else {
      next.hour = padNumber(typed, 2)
    }
  }
  const minute = parseSegment(next.minute ?? '')
  if (minute !== null) {
    next.minute = padNumber(clampToRange(minute, 0, 59), 2)
  }
  return next
}

function stepHour(
  text: SegmentText,
  delta: 1 | -1,
  cycle: MeridiemCycle | null
): { text: SegmentText; carry?: -1 | 1 } {
  const current = canonicalHour(text, cycle)
  if (current === null) {
    // Initialize like a fresh dial: the bottom of the displayed range, honoring the meridiem.
    const init =
      cycle !== null ? fromMeridiemHour(cycle === 11 ? 0 : 1, displayedMeridiem(text)) : 0
    return { text: putHour(text, init, cycle) }
  }
  const hour = wrapToRange(current + delta, 0, 23)
  const crossedMidnight = delta === 1 ? hour === 0 : hour === 23
  const next = putHour(text, hour, cycle)
  return crossedMidnight ? { text: next, carry: delta } : { text: next }
}

function stepMinute(
  text: SegmentText,
  delta: 1 | -1,
  cycle: MeridiemCycle | null
): { text: SegmentText; carry?: -1 | 1 } {
  const minute = parseSegment(text.minute ?? '')
  if (minute === null) {
    return { text: { ...text, minute: '00' } }
  }
  const hour = canonicalHour(text, cycle)
  if (hour === null) {
    // No hour to carry into; step the minute dial alone.
    return { text: { ...text, minute: padNumber(wrapToRange(minute + delta, 0, 59), 2) } }
  }
  const total = hour * 60 + minute + delta
  const wrapped = wrapToRange(total, 0, 1439)
  const next = putHour(
    { ...text, minute: padNumber(wrapped % 60, 2) },
    Math.floor(wrapped / 60),
    cycle
  )
  const carry = total < 0 ? -1 : total > 1439 ? 1 : undefined
  return carry === undefined ? { text: next } : { text: next, carry }
}

function stepTime(
  text: SegmentText,
  key: string,
  delta: 1 | -1,
  cycle: MeridiemCycle | null
): { text: SegmentText; carry?: -1 | 1 } {
  if (key === 'hour') {
    return stepHour(text, delta, cycle)
  }
  if (key === 'minute') {
    return stepMinute(text, delta, cycle)
  }
  if (key === 'meridiem') {
    const current = displayedMeridiem(text)
    return { text: { ...text, meridiem: current === 'AM' ? 'PM' : 'AM' } }
  }
  return { text }
}

function makeTimeField(hourCycle: HourCycle, labels: TimeLabels): FieldType<TimeValue> {
  // The meridiem cycle (h11/h12) drives the AM/PM segment and the display conversion; `null` is the
  // 24-hour mode, where the displayed hour is already canonical and there is no meridiem.
  const cycle: MeridiemCycle | null = hourCycle === 24 ? null : hourCycle
  const segments: Segment[] = [
    { key: 'hour', ariaLabel: labels.hours, widthCh: 2, pad: 2, placeholder: '--', options: [] },
    { key: 'minute', ariaLabel: labels.minutes, widthCh: 2, pad: 2, placeholder: '--', options: [] }
  ]
  if (cycle !== null) {
    segments.push({
      key: 'meridiem',
      ariaLabel: labels.meridiem,
      widthCh: 2.5,
      pad: null,
      placeholder: '',
      // A space before AM/PM instead of the field's ':' (so it reads "02:05 PM", not "02:05:PM").
      separatorBefore: ' ',
      options: MERIDIEMS,
      valueText: (text) => (text === '' ? undefined : untranslated(text))
    })
  }
  return {
    segments,
    separator: ':',
    toText: (time, prev) => {
      if (time === null) {
        return { hour: '', minute: '', meridiem: prev.meridiem ?? 'AM' }
      }
      if (cycle === null) {
        return { hour: padNumber(time.hour, 2), minute: padNumber(time.minute, 2) }
      }
      const { displayHour, meridiem } = toMeridiemHour(time.hour, cycle)
      return { hour: padNumber(displayHour, 2), minute: padNumber(time.minute, 2), meridiem }
    },
    toValue: (text) => {
      const hour = parseSegment(text.hour ?? '')
      const minute = parseSegment(text.minute ?? '')
      if (hour === null || minute === null) {
        return null
      }
      return {
        hour: cycle !== null ? fromMeridiemHour(hour, displayedMeridiem(text)) : hour,
        minute
      }
    },
    normalize: (text) => normalizeTime(text, cycle),
    step: (text, key, delta) => stepTime(text, key, delta, cycle),
    // 0-23 is typeable in every cycle, so a leading 1 or 2 may still grow into 1x / 2x.
    isComplete: (key, digits) => digitsAreComplete(digits, 2, key === 'hour' ? 23 : 59),
    // Spinbutton bounds match the displayed range: 24h hour 0-23, 12h 1-12, 11h 0-11; minute 0-59.
    // The meridiem is non-numeric, so it exposes no min/max.
    bounds: (key) => {
      if (key === 'hour') {
        return cycle === null
          ? { min: 0, max: 23 }
          : cycle === 12
            ? { min: 1, max: 12 }
            : { min: 0, max: 11 }
      }
      if (key === 'minute') {
        return { min: 0, max: 59 }
      }
      return undefined
    },
    typeChar: (text, key, char) => {
      if (key !== 'meridiem') {
        return undefined
      }
      const match = MERIDIEMS.find((option) => option.toLowerCase().startsWith(char.toLowerCase()))
      return match === undefined ? undefined : { ...text, meridiem: match }
    }
  }
}

/** Reactive time {@link FieldType} for a `<SegmentedField>`. */
export function useTimeField(
  hourCycle: MaybeRefOrGetter<HourCycle>
): ComputedRef<FieldType<TimeValue>> {
  const { _t } = usei18n()
  const labels: TimeLabels = {
    hours: _t('Hours'),
    minutes: _t('Minutes'),
    meridiem: _t('AM or PM')
  }
  return computed(() => makeTimeField(toValue(hourCycle), labels))
}
