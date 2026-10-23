/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ZonedDateTime, fromAbsolute, getLocalTimeZone } from '@internationalized/date'

/** A point in time: unix seconds or a `Date`. */
export type Instant = number | Date

function toZoned(at: Instant, timeZone: string): ZonedDateTime {
  const ms = at instanceof Date ? at.getTime() : at * 1000
  return fromAbsolute(ms, timeZone)
}

function pad(value: number, width: number = 2): string {
  return String(value).padStart(width, '0')
}

/** `2025-02-23`, like `cmk.utils.render.date`. */
export function renderDate(at: Instant, timeZone: string = getLocalTimeZone()): string {
  const zdt = toZoned(at, timeZone)
  return `${pad(zdt.year, 4)}-${pad(zdt.month)}-${pad(zdt.day)}`
}

/** `17:47:59`, like `cmk.utils.render.time_of_day`. */
export function renderTimeOfDay(at: Instant, timeZone: string = getLocalTimeZone()): string {
  const zdt = toZoned(at, timeZone)
  return `${pad(zdt.hour)}:${pad(zdt.minute)}:${pad(zdt.second)}`
}

/** `2025-02-23 17:47:59`, like `cmk.utils.render.date_and_time`. */
export function renderDateAndTime(at: Instant, timeZone: string = getLocalTimeZone()): string {
  return `${renderDate(at, timeZone)} ${renderTimeOfDay(at, timeZone)}`
}
