/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeRange } from '@/graphing/components/TimeSeriesGraph'
import type { BinUnit, GridStep } from '@/graphing/utils/bins'

export const MINUTE = 60
export const HOUR = 3600
export const DAY = 86_400

export interface LocalTimeCase {
  name: string
  timeZone: string
  /** The instant of an offset change of the zone, or any instant for a zone without one. */
  instant: number
  change: 'forward' | 'back' | null
  /** The coarsest step that meets every local bin edge of the zone. */
  gridStep: GridStep
}

function at(iso: string): number {
  return Date.parse(iso) / 1000
}

// prettier-ignore
export const LOCAL_TIME_CASES: LocalTimeCase[] = [
  { name: 'UTC', timeZone: 'UTC', instant: at('2026-06-15T10:00Z'), change: null, gridStep: 3600 },
  { name: 'whole-hour offset, clocks forward', timeZone: 'Europe/Berlin', instant: at('2026-03-29T01:00Z'), change: 'forward', gridStep: 3600 },
  { name: 'whole-hour offset, clocks back', timeZone: 'Europe/Berlin', instant: at('2026-10-25T01:00Z'), change: 'back', gridStep: 3600 },
  { name: 'negative offset, clocks forward', timeZone: 'America/New_York', instant: at('2026-03-08T07:00Z'), change: 'forward', gridStep: 3600 },
  { name: 'negative offset, clocks back', timeZone: 'America/New_York', instant: at('2026-11-01T06:00Z'), change: 'back', gridStep: 3600 },
  { name: 'negative half-hour offset, clocks forward', timeZone: 'America/St_Johns', instant: at('2026-03-08T05:30Z'), change: 'forward', gridStep: 1800 },
  { name: 'negative half-hour offset, clocks back', timeZone: 'America/St_Johns', instant: at('2026-11-01T04:30Z'), change: 'back', gridStep: 1800 },
  { name: 'half-hour offset', timeZone: 'Asia/Kolkata', instant: at('2026-06-15T10:00Z'), change: null, gridStep: 1800 },
  { name: 'quarter-hour offset', timeZone: 'Asia/Kathmandu', instant: at('2026-06-15T10:00Z'), change: null, gridStep: 900 },
  { name: 'quarter-hour offset, clocks forward', timeZone: 'Pacific/Chatham', instant: at('2026-09-26T14:00Z'), change: 'forward', gridStep: 900 },
  { name: 'quarter-hour offset, clocks back', timeZone: 'Pacific/Chatham', instant: at('2026-04-04T14:00Z'), change: 'back', gridStep: 900 },
  { name: 'half-hour shift, clocks forward', timeZone: 'Australia/Lord_Howe', instant: at('2026-10-03T15:30Z'), change: 'forward', gridStep: 1800 },
  { name: 'half-hour shift, clocks back', timeZone: 'Australia/Lord_Howe', instant: at('2026-04-04T15:00Z'), change: 'back', gridStep: 1800 },
  { name: 'clocks forward at midnight, no midnight', timeZone: 'America/Santiago', instant: at('2026-09-06T04:00Z'), change: 'forward', gridStep: 3600 },
  { name: 'clocks back at midnight', timeZone: 'America/Santiago', instant: at('2026-04-05T03:00Z'), change: 'back', gridStep: 3600 },
  { name: 'clocks back after midnight, two midnights', timeZone: 'America/Havana', instant: at('2026-11-01T05:00Z'), change: 'back', gridStep: 3600 }
]

export interface WindowShape {
  name: string
  window(unit: BinUnit, timeZone: string, instant: number): { start: number; end: number }
}

// prettier-ignore
export const WINDOW_SHAPES: WindowShape[] = [
  { name: 'a long window', window: (unit, _timeZone, instant) => windowAround(unit, instant) },
  { name: 'a window inside one bin', window: (_unit, _timeZone, instant) => ({ start: instant + MINUTE, end: instant + 9 * MINUTE }) },
  { name: 'a window from a bin edge', window: (unit, timeZone, instant) => {
    const start = expectedBinEdges(unit, timeZone, { start: instant, end: instant + 1 })[0]!
    return { start, end: start + 3 * (unit === 'hour' ? HOUR : DAY) + 17 * MINUTE }
  } }
]

/** A window around the case that starts and ends inside a bin of the unit. */
export function windowAround(unit: BinUnit, instant: number): { start: number; end: number } {
  const reach = unit === 'hour' ? 36 * HOUR : 3 * DAY
  return { start: instant - reach + 7 * MINUTE + 13, end: instant + reach + 23 * MINUTE + 41 }
}

interface LocalClock {
  date: string
  hour: string
  offset: string
}

const formatters = new Map<string, Intl.DateTimeFormat>()

function localClock(time: number, timeZone: string): LocalClock {
  let formatter = formatters.get(timeZone)
  if (formatter === undefined) {
    formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      hourCycle: 'h23',
      timeZoneName: 'longOffset'
    })
    formatters.set(timeZone, formatter)
  }
  const parts = Object.fromEntries(
    formatter.formatToParts(new Date(time * 1000)).map((part) => [part.type, part.value])
  )
  return {
    date: `${parts['year']}-${parts['month']}-${parts['day']}`,
    hour: parts['hour']!,
    offset: parts['timeZoneName']!
  }
}

export function offsetAt(time: number, timeZone: string): string {
  return localClock(time, timeZone).offset
}

// Every offset change and every local hour start of the cases falls on a UTC quarter hour.
const SCAN_STEP = 15 * MINUTE
// One bin before and after the interval, and no bin is longer than a 25-hour day.
const SCAN_MARGIN = 26 * HOUR

/**
 * The instants that start a local bin, found by scanning the local clock: an hour starts where the
 * local hour or the offset changes, a day where a local date begins that the clock has not shown
 * before.
 */
function localBinStarts(unit: BinUnit, timeZone: string, from: number, to: number): number[] {
  const starts: number[] = []
  const first = Math.ceil(from / SCAN_STEP) * SCAN_STEP
  let previous = localClock(first - SCAN_STEP, timeZone)
  let latestDate = previous.date
  for (let time = first; time <= to; time += SCAN_STEP) {
    const now = localClock(time, timeZone)
    const startsHour = now.hour !== previous.hour || now.offset !== previous.offset
    const startsDay = now.date > latestDate
    if (unit === 'hour' ? startsHour : startsDay) {
      starts.push(time)
    }
    if (now.date > latestDate) {
      latestDate = now.date
    }
    previous = now
  }
  return starts
}

/** The local bin edges that cover the interval, read off the local clock. */
export function expectedBinEdges(
  unit: BinUnit,
  timeZone: string,
  interval: { start: number; end: number }
): number[] {
  const starts = localBinStarts(
    unit,
    timeZone,
    interval.start - SCAN_MARGIN,
    interval.end + SCAN_MARGIN
  )
  const first = starts.findIndex((start) => start > interval.start) - 1
  const last = starts.findIndex((start) => start >= interval.end)
  return starts.slice(first, last + 1)
}

export const BIN_UNITS: BinUnit[] = ['hour', 'day']

export interface ServedGrid {
  name: string
  /** Null for the step the fetch plans, which meets every bin edge. */
  step: number | null
  phase: number
}

export const PLANNED_GRID: ServedGrid = { name: 'planned grid', step: null, phase: 0 }
export const SHIFTED_QUARTER_HOUR_GRID: ServedGrid = {
  name: 'shifted quarter-hour grid',
  step: 15 * MINUTE,
  phase: 5 * MINUTE
}
export const SIX_HOUR_GRID: ServedGrid = { name: 'six-hour grid', step: 6 * HOUR, phase: 0 }

/** One grid that meets every bin edge, one that misses them, and one coarser than a bin. */
export const SERVED_GRIDS: ServedGrid[] = [PLANNED_GRID, SHIFTED_QUARTER_HOUR_GRID, SIX_HOUR_GRID]

/** The served grid that covers the interval with a grid value to spare on each side. */
export function servedGrid(
  grid: ServedGrid,
  interval: { start: number; end: number },
  plannedStep: number
): TimeRange {
  const step = grid.step ?? plannedStep
  const start = Math.floor((interval.start - grid.phase) / step) * step + grid.phase - step
  const end = Math.ceil((interval.end - grid.phase) / step) * step + grid.phase + step
  return { start, end, step }
}

export function ones(grid: TimeRange): number[] {
  return Array.from({ length: (grid.end - grid.start) / grid.step }, () => 1)
}

/** The number of grid values that reach into the interval. */
export function gridValuesReaching(grid: TimeRange, interval: { start: number; end: number }) {
  return ones(grid).filter((_, index) => {
    const valueStart = grid.start + index * grid.step
    return valueStart < interval.end && valueStart + grid.step > interval.start
  }).length
}
