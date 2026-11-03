/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { renderDate, renderTimeOfDay } from 'cmk-ui-library/lib/renderTime'

import type { DateFormatId, DisplayOptions } from '@/monitoring/shared/types'

function formatDate(unixSeconds: number, format: DateFormatId): string {
  const [year, month, day] = renderDate(unixSeconds).split('-')
  switch (format) {
    case '%d.%m.%Y':
      return `${day}.${month}.${year}`
    case '%m/%d/%Y':
      return `${month}/${day}/${year}`
    case '%d.%m.':
      return `${day}.${month}.`
    case '%m/%d':
      return `${month}/${day}`
    case '%Y-%m-%d':
      return `${year}-${month}-${day}`
  }
}

function formatAbsolute(unixSeconds: number, dateFormat: DateFormatId): string {
  return `${formatDate(unixSeconds, dateFormat)} ${renderTimeOfDay(unixSeconds)}`
}

/**
 * Approximates a duration in the coarsest unit that still says something, mirroring
 * `cmk.utils.render.approx_age`'s practical range for check ages. Its fs/ps/ns/µs
 * branches never apply here, since ages are measured against a millisecond-resolution
 * clock, but sub-second ages do occur, e.g. right after a check just ran, and render in
 * ms like the legacy renderer. Units are abbreviations, not translated, matching the
 * legacy renderer. Unlike it, an age that rounds up into the next range renders in that
 * range: 0.9996 s as "1.00 s", not "1000 ms", and 9.996 s as "10.0 s", not "10.00 s".
 * Age columns are sized by the longest text this renders, which the extra digit would widen.
 */
function formatApproxAge(seconds: number): string {
  const milliseconds = seconds * 1000
  if (milliseconds < 999.5) {
    return `${Math.round(milliseconds)} ms`
  }
  if (seconds < 9.995) {
    return `${seconds.toFixed(2)} s`
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`
  }
  if (seconds < 240) {
    return `${Math.trunc(seconds)} s`
  }
  const minutes = seconds / 60
  if (minutes < 360) {
    return `${Math.trunc(minutes)} m`
  }
  const hours = minutes / 60
  if (hours < 48) {
    return `${Math.trunc(hours)} h`
  }
  const days = hours / 24
  if (days < 6) {
    return `${days.toFixed(1).replace(/\.0$/, '')} d`
  }
  if (days < 999) {
    return `${Math.round(days)} d`
  }
  const years = days / 365
  if (years < 10) {
    return `${years.toFixed(1)} y`
  }
  return `${Math.round(years)} y`
}

// The longest text `formatApproxAge` renders, with every digit as `0`: "999 ms". Every other
// branch renders at most three digits, one space and a one-letter unit, plus at most a `.`,
// which together are no wider than these.
const LONGEST_APPROX_AGE_SHAPE = '000 ms'

function formatRelative(unixSeconds: number): string {
  const ageSeconds = Date.now() / 1000 - unixSeconds
  return ageSeconds < 0 ? `in ${formatApproxAge(-ageSeconds)}` : formatApproxAge(ageSeconds)
}

/**
 * The longest text `formatDisplayTimestamp` renders with these options, with every digit as `0`.
 * It leaves out the `in` of a future timestamp's age, which only clocks running apart produce, so
 * such an age may wrap.
 */
export function longestTimestampShape(options: DisplayOptions): string {
  const date = formatAbsolute(0, options.dateFormat).replace(/\d/g, '0')
  const age = LONGEST_APPROX_AGE_SHAPE
  switch (options.timestampFormat) {
    case 'epoch':
      // Ten digits until the year 2286.
      return '0000000000'
    case 'abs':
    case 'mixed':
      // Even the shortest date has seven digits more than the longest age.
      return date
    case 'rel':
      return age
    case 'both':
      return `${date} - ${age}`
  }
}

/**
 * Renders a unix timestamp per the "Modify display options" pane's Date Format and
 * Timestamp Format choices, mirroring `paint_age` (`cmk/gui/painter_options.py`).
 */
export function formatDisplayTimestamp(unixSeconds: number, options: DisplayOptions): string {
  if (options.timestampFormat === 'epoch') {
    return String(Math.trunc(unixSeconds))
  }
  if (options.timestampFormat === 'both') {
    return `${formatAbsolute(unixSeconds, options.dateFormat)} - ${formatRelative(unixSeconds)}`
  }
  const ageSeconds = Date.now() / 1000 - unixSeconds
  const useAbsolute =
    options.timestampFormat === 'abs' ||
    (options.timestampFormat === 'mixed' && Math.abs(ageSeconds) >= 48 * 3600)
  return useAbsolute ? formatAbsolute(unixSeconds, options.dateFormat) : formatRelative(unixSeconds)
}
