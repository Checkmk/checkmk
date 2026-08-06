/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export type TimerangeModel = components['schemas']['TimerangeModel']
export type PreDefinedTimeRange = components['schemas']['_Predefined']

export interface EpochTimeRange {
  start: number
  end: number
}

const toEpochSeconds = (date: Date): number => Math.floor(date.getTime() / 1000)

const startOfDay = (date: Date): Date =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate())

// Checkmk weeks start on Monday.
const startOfWeek = (date: Date): Date => {
  const day = startOfDay(date)
  day.setDate(day.getDate() - ((day.getDay() + 6) % 7))
  return day
}

const startOfMonth = (date: Date): Date => new Date(date.getFullYear(), date.getMonth(), 1)

const startOfYear = (date: Date): Date => new Date(date.getFullYear(), 0, 1)

// Calendar arithmetic (instead of fixed 86400s steps) keeps day boundaries correct across DST.
const addDays = (date: Date, days: number): Date => {
  const result = new Date(date)
  result.setDate(result.getDate() + days)
  return result
}

const addMonths = (date: Date, months: number): Date =>
  new Date(date.getFullYear(), date.getMonth() + months, date.getDate())

const addYears = (date: Date, years: number): Date =>
  new Date(date.getFullYear() + years, date.getMonth(), date.getDate())

const parseIsoDateAsLocal = (value: string): Date => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year!, month! - 1, day!)
}

const spanOf = (start: Date, end: Date): EpochTimeRange => ({
  start: toEpochSeconds(start),
  end: toEpochSeconds(end)
})

const assertNever = (value: never): never => {
  throw new Error(`Unhandled predefined time range: ${String(value)}`)
}

// Handles every `_Predefined` key (the exhaustive switch is enforced by `assertNever`, so a new
// backend key fails the build here instead of silently falling back to a wrong window). Trailing
// "last N …" windows end at "now"; the calendar ranges snap to local day/week/month/year edges.
const computePredefined = (value: PreDefinedTimeRange, now: Date): EpochTimeRange => {
  const nowSeconds = toEpochSeconds(now)
  const today = startOfDay(now)
  const thisWeek = startOfWeek(now)
  const thisMonth = startOfMonth(now)
  const thisYear = startOfYear(now)
  switch (value) {
    case 'last_4_hours':
      return { start: nowSeconds - 4 * 3600, end: nowSeconds }
    case 'last_25_hours':
      return { start: nowSeconds - 25 * 3600, end: nowSeconds }
    case 'last_8_days':
      return { start: toEpochSeconds(addDays(now, -8)), end: nowSeconds }
    case 'last_35_days':
      return { start: toEpochSeconds(addDays(now, -35)), end: nowSeconds }
    case 'last_400_days':
      return { start: toEpochSeconds(addDays(now, -400)), end: nowSeconds }
    case 'today':
      return { start: toEpochSeconds(today), end: nowSeconds }
    case 'yesterday':
      return spanOf(addDays(today, -1), today)
    case '7_days_ago':
      return spanOf(addDays(today, -7), addDays(today, -6))
    case '8_days_ago':
      return spanOf(addDays(today, -8), addDays(today, -7))
    case 'this_week':
      return { start: toEpochSeconds(thisWeek), end: nowSeconds }
    case 'last_week':
      return spanOf(addDays(thisWeek, -7), thisWeek)
    case '2_weeks_ago':
      return spanOf(addDays(thisWeek, -14), addDays(thisWeek, -7))
    case 'this_month':
      return { start: toEpochSeconds(thisMonth), end: nowSeconds }
    case 'last_month':
      return spanOf(addMonths(thisMonth, -1), thisMonth)
    case 'this_year':
      return { start: toEpochSeconds(thisYear), end: nowSeconds }
    case 'last_year':
      return spanOf(addYears(thisYear, -1), thisYear)
    default:
      return assertNever(value)
  }
}

/**
 * Compute the epoch-seconds window a configured time range denotes right now.
 *
 * Mirrors the backend's `Timerange.compute_range` semantics (in browser-local time): trailing
 * windows end at "now", calendar ranges snap to local day/week/month/year boundaries, and fixed
 * date ranges include the end day.
 */
export const computeEpochTimeRange = (
  model: TimerangeModel,
  now: Date = new Date()
): EpochTimeRange => {
  switch (model.type) {
    case 'graph':
      return { start: toEpochSeconds(now) - model.duration, end: toEpochSeconds(now) }
    case 'age': {
      const age =
        (model.days ?? 0) * 86400 +
        (model.hours ?? 0) * 3600 +
        (model.minutes ?? 0) * 60 +
        (model.seconds ?? 0)
      return { start: toEpochSeconds(now) - age, end: toEpochSeconds(now) }
    }
    case 'date':
      // The configured end day is included in the range.
      return spanOf(parseIsoDateAsLocal(model.start), addDays(parseIsoDateAsLocal(model.end), 1))
    case 'predefined':
      return computePredefined(model.value, now)
  }
}
