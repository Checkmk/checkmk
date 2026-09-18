/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// The timezone is injected (rather than read from the ambient local zone) so the axis is
// deterministic and testable across zones. Label widths are measured, so tick density follows the
// text that is really drawn.
import {
  type ZonedDateTime,
  fromAbsolute,
  getLocalTimeZone,
  startOfMonth,
  startOfWeek
} from '@internationalized/date'

import { isoDate, pad2, shortWeekday } from '@/graphing/utils/timeFormat'

import type { TimeRange } from '../types'

export function timestampAt(timeRange: TimeRange, valueIndex: number): number {
  return timeRange.start + (valueIndex + 1) * timeRange.step
}

const SECONDS_PER_DAY = 86_400

const MIN_LABEL_GAP_PX = 24

export interface TimeAxisTick {
  position: number
  text: string | null
  lineWidth: number
}

export type MeasureLabel = (text: string) => number

interface Labelling {
  format: string
  labelShift: number
  labelDistanceAtLeast: number
}

function pickLabelling(start: ZonedDateTime, end: ZonedDateTime, timeRangeDays: number): Labelling {
  const sameYear = start.year === end.year
  const sameMonth = sameYear && start.month === end.month
  const sameDate = sameMonth && start.day === end.day

  if (sameDate) {
    return { format: '%H:%M', labelShift: 0, labelDistanceAtLeast: 0 }
  }
  if (timeRangeDays < 7) {
    return { format: '%a %H:%M', labelShift: 0, labelDistanceAtLeast: 0 }
  }
  if (timeRangeDays < 32 && sameMonth) {
    return {
      format: '%d',
      labelShift: SECONDS_PER_DAY / 2,
      labelDistanceAtLeast: SECONDS_PER_DAY
    }
  }
  if (sameYear) {
    return { format: '%m-%d', labelShift: 0, labelDistanceAtLeast: 0 }
  }
  return { format: '%Y-%m-%d', labelShift: 0, labelDistanceAtLeast: 0 }
}

// Every label of a given format has the same digit count, so one sample stands in for all of them.
const WIDEST_LABEL_SAMPLE: Record<string, string> = {
  '%H:%M': '00:00',
  '%d': '00',
  '%m-%d': '00-00',
  '%Y-%m-%d': '0000-00-00'
}

const DAYS_PER_WEEK = 7

function widestLabelWidth(
  labelling: Labelling,
  start: ZonedDateTime,
  measureLabel: MeasureLabel
): number {
  if (labelling.format === '%a %H:%M') {
    let widest = 0
    for (let dayOffset = 0; dayOffset < DAYS_PER_WEEK; dayOffset++) {
      const label = formatLabel(labelling.format, start.add({ days: dayOffset }))
      widest = Math.max(widest, measureLabel(label))
    }
    return widest
  }
  return measureLabel(WIDEST_LABEL_SAMPLE[labelling.format] ?? WIDEST_LABEL_SAMPLE['%Y-%m-%d']!)
}

function formatLabel(format: string, zdt: ZonedDateTime): string {
  const hhmm = `${pad2(zdt.hour)}:${pad2(zdt.minute)}`
  switch (format) {
    case '%H:%M':
      return hhmm
    case '%a %H:%M':
      return `${shortWeekday(zdt.toDate().getTime() / 1000, zdt.timeZone)} ${hhmm}`
    case '%d':
      return pad2(zdt.day)
    case '%m-%d':
      return `${pad2(zdt.month)}-${pad2(zdt.day)}`
    default:
      return isoDate(zdt)
  }
}

function startOfDay(zdt: ZonedDateTime): ZonedDateTime {
  return zdt.set({ hour: 0, minute: 0, second: 0, millisecond: 0 })
}

function tAxisLabels(
  start: ZonedDateTime,
  end: ZonedDateTime,
  addStep: (zdt: ZonedDateTime) => ZonedDateTime,
  initialPosition: ZonedDateTime
): ZonedDateTime[] {
  const positions: ZonedDateTime[] = []
  let position = initialPosition.compare(start) < 0 ? addStep(initialPosition) : initialPosition
  while (position.compare(end) <= 0) {
    positions.push(position)
    position = addStep(position)
  }
  return positions
}

function secondsProducer(
  start: ZonedDateTime,
  end: ZonedDateTime,
  stepSeconds: number
): ZonedDateTime[] {
  const midnight = startOfDay(start)
  const secondsSinceMidnight = Math.floor(
    (start.toDate().getTime() - midnight.toDate().getTime()) / 1000
  )
  const initialOffset = Math.floor(secondsSinceMidnight / stepSeconds) * stepSeconds
  const initialPosition = midnight.add({ seconds: initialOffset })
  return tAxisLabels(start, end, (zdt) => zdt.add({ seconds: stepSeconds }), initialPosition)
}

function daysProducer(start: ZonedDateTime, end: ZonedDateTime, stepDays: number): ZonedDateTime[] {
  return tAxisLabels(start, end, (zdt) => zdt.add({ days: stepDays }), startOfDay(start))
}

function weekProducer(start: ZonedDateTime, end: ZonedDateTime): ZonedDateTime[] {
  const initialPosition = startOfDay(startOfWeek(start, 'en-GB'))
  return tAxisLabels(start, end, (zdt) => zdt.add({ weeks: 1 }), initialPosition)
}

function monthsProducer(
  start: ZonedDateTime,
  end: ZonedDateTime,
  stepMonths: number
): ZonedDateTime[] {
  const initialPosition = startOfDay(startOfMonth(start))
  return tAxisLabels(start, end, (zdt) => zdt.add({ months: stepMonths }), initialPosition)
}

function selectTickProducer(
  minDistance: number
): (start: ZonedDateTime, end: ZonedDateTime) => ZonedDateTime[] {
  for (const distMinutes of [1, 2, 5, 10, 20, 30, 60, 120, 240, 360, 480, 720]) {
    if (minDistance <= distMinutes * 60) {
      const stepSeconds = distMinutes * 60
      return (start, end) => secondsProducer(start, end, stepSeconds)
    }
  }
  for (const distDays of [1, 2, 3, 4]) {
    if (minDistance <= distDays * SECONDS_PER_DAY) {
      return (start, end) => daysProducer(start, end, distDays)
    }
  }
  if (minDistance <= SECONDS_PER_DAY * 7) {
    return (start, end) => weekProducer(start, end)
  }
  for (const stepMonths of [1, 2, 3, 4, 6, 12, 18, 24, 36, 48]) {
    if (minDistance <= SECONDS_PER_DAY * 31 * stepMonths) {
      return (start, end) => monthsProducer(start, end, stepMonths)
    }
  }
  return (start, end) => monthsProducer(start, end, 96)
}

export function computeTimeAxis(
  startTime: number,
  endTime: number,
  plotWidth: number,
  step: number,
  measureLabel: MeasureLabel,
  timeZone: string = getLocalTimeZone()
): TimeAxisTick[] {
  const secondsPerPixel = (endTime - startTime) / Math.max(plotWidth, 1)
  const positionToX = (position: number): number => (position - startTime) / secondsPerPixel

  const firstTickTime = startTime + step
  const lastTickTime = endTime - step
  const timeRange = lastTickTime - firstTickTime
  if (timeRange <= 0) {
    return []
  }

  const startZoned = fromAbsolute(firstTickTime * 1000, timeZone)
  const endZoned = fromAbsolute(lastTickTime * 1000, timeZone)
  const timeRangeDays = timeRange / SECONDS_PER_DAY

  const labelling = pickLabelling(startZoned, endZoned, timeRangeDays)
  const requiredDistance =
    (widestLabelWidth(labelling, startZoned, measureLabel) + MIN_LABEL_GAP_PX) * secondsPerPixel
  const producer = selectTickProducer(
    // Half the range is the floor the backend also keeps (its label count bottoms out at two), so
    // even a plot too narrow for a single label still gets a couple of grid lines.
    Math.max(labelling.labelDistanceAtLeast, Math.min(requiredDistance, timeRange / 2))
  )

  const ticks: TimeAxisTick[] = []
  const emittedLabels = new Set<string>()
  let previousLabelRightEdge = -Infinity
  for (const positionZoned of producer(startZoned, endZoned)) {
    let lineWidth = 2
    let position = Math.round(positionZoned.toDate().getTime() / 1000)
    let label: string | null = formatLabel(labelling.format, positionZoned)

    if (labelling.labelShift) {
      ticks.push({ position, text: null, lineWidth })
      lineWidth = 0
      position += labelling.labelShift
    }

    // A DST fall-back repeats a local hour, so wall-clock labels ("02:00") would show up
    // twice (hour-level counterpart of Werk #14830). Keep the tick but suppress the
    // repeated label so every rendered label stays unambiguous.
    if (label !== null && emittedLabels.has(label)) {
      label = null
    }
    if (label !== null) {
      const halfWidth = measureLabel(label) / 2
      const center = positionToX(position)
      const overlapsPrevious = center - halfWidth < previousLabelRightEdge + MIN_LABEL_GAP_PX
      const overflowsPlot = center - halfWidth < 0 || center + halfWidth > plotWidth
      if (overlapsPrevious || overflowsPlot) {
        label = null
      } else {
        emittedLabels.add(label)
        previousLabelRightEdge = center + halfWidth
      }
    }
    ticks.push({ position, text: label, lineWidth })
  }
  return ticks
}
