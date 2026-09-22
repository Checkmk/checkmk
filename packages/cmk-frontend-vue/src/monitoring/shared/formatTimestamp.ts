/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateFormatId, DisplayOptions } from '@/monitoring/shared/types'

/** Renders a unix timestamp as `YYYY-MM-DD HH:MM:SS` in the viewer's local time. */
export function formatTimestamp(unixSeconds: number): string {
  const date = new Date(unixSeconds * 1000)
  const pad = (value: number): string => String(value).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

function formatDate(date: Date, format: DateFormatId): string {
  const pad = (value: number): string => String(value).padStart(2, '0')
  const year = date.getFullYear()
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
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
  const date = new Date(unixSeconds * 1000)
  const pad = (value: number): string => String(value).padStart(2, '0')
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  return `${formatDate(date, dateFormat)} ${time}`
}

/**
 * Approximates a duration in the coarsest unit that still says something, mirroring
 * `cmk.utils.render.approx_age`'s practical range for check ages. Its fs/ps/ns/µs
 * branches never apply here, since ages are measured against a millisecond-resolution
 * clock, but sub-second ages do occur, e.g. right after a check just ran, and render in
 * ms like the legacy renderer. Units are abbreviations, not translated, matching the
 * legacy renderer.
 */
function formatApproxAge(seconds: number): string {
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)} ms`
  }
  if (seconds < 10) {
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

function formatRelative(unixSeconds: number): string {
  const ageSeconds = Date.now() / 1000 - unixSeconds
  return ageSeconds < 0 ? `in ${formatApproxAge(-ageSeconds)}` : formatApproxAge(ageSeconds)
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
