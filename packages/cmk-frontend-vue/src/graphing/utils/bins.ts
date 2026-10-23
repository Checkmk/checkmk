/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromAbsolute, toCalendarDate, toZoned } from '@internationalized/date'

import type { TimeInterval, TimeRange } from '../types'

export type BinUnit = 'hour' | 'day'
export type BinAggregation = 'sum'
export type GridStep = 3600 | 1800 | 900

export interface Bin {
  start: number
  end: number
  /** Null when no grid value inside the bin holds data. */
  value: number | null
}

const SECONDS_PER_HOUR = 3600
const SECONDS_PER_DAY = 86_400
const MIN_BAR_WIDTH_PX = 3
const GRID_STEPS_LARGEST_FIRST: GridStep[] = [3600, 1800, 900]
const FINEST_GRID_STEP: GridStep = 900

/** The nominal length of a bin; a local day around a DST change is an hour shorter or longer. */
export const BIN_UNIT_SECONDS: Record<BinUnit, number> = {
  hour: SECONDS_PER_HOUR,
  day: SECONDS_PER_DAY
}

function offsetSeconds(time: number, timeZone: string): number {
  return fromAbsolute(time * 1000, timeZone).offset / 1000
}

function offsetShiftBetween(before: number, after: number, timeZone: string): number {
  const offset = offsetSeconds(after, timeZone)
  let low = before
  let high = after
  while (high - low > 1) {
    const middle = Math.floor((low + high) / 2)
    if (offsetSeconds(middle, timeZone) === offset) {
      high = middle
    } else {
      low = middle
    }
  }
  return high
}

function startOfLocalHour(time: number, timeZone: string): number {
  const offset = offsetSeconds(time, timeZone)
  const localSeconds = time + offset
  const floor = time - (((localSeconds % SECONDS_PER_HOUR) + SECONDS_PER_HOUR) % SECONDS_PER_HOUR)
  // A DST shift inside a local hour, as at a half-hour shift or at 02:45, restarts the hour.
  return offsetSeconds(floor, timeZone) === offset
    ? floor
    : offsetShiftBetween(floor, time, timeZone)
}

function startOfNextLocalHour(hourStart: number, timeZone: string): number {
  const next = startOfLocalHour(hourStart + SECONDS_PER_HOUR, timeZone)
  return offsetSeconds(hourStart, timeZone) === offsetSeconds(next, timeZone)
    ? next
    : offsetShiftBetween(hourStart, next, timeZone)
}

function startOfLocalDay(time: number, timeZone: string): number {
  const date = toCalendarDate(fromAbsolute(time * 1000, timeZone))
  return toZoned(date, timeZone).toDate().getTime() / 1000
}

function startOfNextLocalDay(dayStart: number, timeZone: string): number {
  const nextDate = toCalendarDate(fromAbsolute(dayStart * 1000, timeZone)).add({ days: 1 })
  return toZoned(nextDate, timeZone).toDate().getTime() / 1000
}

/** The start of the local-time bin that holds the time. */
export function binStart(unit: BinUnit, time: number, timeZone: string): number {
  switch (unit) {
    case 'hour':
      return startOfLocalHour(time, timeZone)
    case 'day':
      return startOfLocalDay(time, timeZone)
  }
}

function nextBinStart(unit: BinUnit, start: number, timeZone: string): number {
  switch (unit) {
    case 'hour':
      return startOfNextLocalHour(start, timeZone)
    case 'day':
      return startOfNextLocalDay(start, timeZone)
  }
}

/** The edges of the local-time bins that cover the interval, in epoch seconds. */
export function binEdges(unit: BinUnit, interval: TimeInterval, timeZone: string): number[] {
  const edges = [binStart(unit, interval.start, timeZone)]
  while (edges[edges.length - 1]! < interval.end) {
    edges.push(nextBinStart(unit, edges[edges.length - 1]!, timeZone))
  }
  return edges
}

/**
 * The step to request for the bins: the coarsest epoch-aligned step that places a grid edge on every
 * bin edge, or the finest one when none does.
 */
export function gridStep(edges: number[]): GridStep {
  return (
    GRID_STEPS_LARGEST_FIRST.find((candidate) => edges.every((edge) => edge % candidate === 0)) ??
    FINEST_GRID_STEP
  )
}

function binOrdinal(unit: BinUnit, edge: number, timeZone: string): number {
  const zoned = fromAbsolute(edge * 1000, timeZone)
  switch (unit) {
    case 'hour':
      return Math.floor((edge + zoned.offset / 1000) / SECONDS_PER_HOUR)
    case 'day':
      return Date.UTC(zoned.year, zoned.month - 1, zoned.day) / 1000 / SECONDS_PER_DAY
  }
}

/**
 * The bin edges to draw over the interval: bins narrower than a bar can be drawn merge into groups
 * that start at a fixed multiple of the unit, so a pan keeps the grouping. A local hour that the
 * clocks repeat or restart starts no second group.
 */
export function drawnBinEdges(
  unit: BinUnit,
  interval: TimeInterval,
  plotWidth: number,
  timeZone: string
): number[] {
  const edges = binEdges(unit, interval, timeZone)
  const binWidthPx = (plotWidth * BIN_UNIT_SECONDS[unit]) / (interval.end - interval.start)
  const binsPerGroup = Math.max(1, Math.ceil(MIN_BAR_WIDTH_PX / binWidthPx))
  if (binsPerGroup === 1) {
    return edges
  }
  let latestOrdinal = -Infinity
  return edges.filter((edge, index) => {
    const ordinal = binOrdinal(unit, edge, timeZone)
    const startsGroup = ordinal > latestOrdinal && ordinal % binsPerGroup === 0
    latestOrdinal = Math.max(latestOrdinal, ordinal)
    return index === 0 || index === edges.length - 1 || startsGroup
  })
}

function gridPhase(grid: TimeRange): number {
  return ((grid.start % grid.step) + grid.step) % grid.step
}

function floorToGrid(time: number, grid: TimeRange): number {
  const phase = gridPhase(grid)
  return phase + Math.floor((time - phase) / grid.step) * grid.step
}

function ceilToGrid(time: number, grid: TimeRange): number {
  const phase = gridPhase(grid)
  return phase + Math.ceil((time - phase) / grid.step) * grid.step
}

function nearestGridEdge(time: number, grid: TimeRange): number {
  const phase = gridPhase(grid)
  return phase + Math.floor((time - phase) / grid.step + 0.5) * grid.step
}

function snapEdgeToGrid(edge: number, index: number, edges: number[], grid: TimeRange): number {
  if (index === 0) {
    return floorToGrid(edge, grid)
  }
  if (index === edges.length - 1) {
    return ceilToGrid(edge, grid)
  }
  return nearestGridEdge(edge, grid)
}

function emptyBins(edges: number[], grid: TimeRange): Bin[] {
  const snapped = [...new Set(edges.map((edge, index) => snapEdgeToGrid(edge, index, edges, grid)))]
  return snapped
    .slice(0, -1)
    .map((start, index) => ({ start, end: snapped[index + 1]!, value: null }))
}

function combine(aggregation: BinAggregation, total: number | null, value: number): number {
  switch (aggregation) {
    case 'sum':
      return (total ?? 0) + value
  }
}

/**
 * Folds the grid values into the bins the edges delimit. The edges snap to the grid first: an inner
 * edge to the nearest grid edge, so a grid value counts in the bin that holds most of it; the outer
 * edges outwards, so the bins hold every grid value that reaches into the edges. A coarser grid
 * merges bins, a shifted grid shifts them.
 */
export function foldIntoBins(
  dataPoints: (number | null)[],
  timeRange: TimeRange,
  edges: number[],
  aggregation: BinAggregation
): Bin[] {
  const bins = emptyBins(edges, timeRange)
  let binIndex = 0
  for (const [index, value] of dataPoints.entries()) {
    const valueStart = timeRange.start + index * timeRange.step
    const valueEnd = valueStart + timeRange.step
    while (binIndex < bins.length && bins[binIndex]!.end <= valueStart) {
      binIndex++
    }
    const bin = bins[binIndex]
    if (bin === undefined || valueEnd <= bin.start) {
      continue
    }
    if (value !== null && Number.isFinite(value)) {
      bin.value = combine(aggregation, bin.value, value)
    }
  }
  return bins
}
