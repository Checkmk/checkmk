/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Ported from cmk/gui/graphing/_artwork.py::_compute_graph_t_axis. Not a literal
// translation but faithful to the backend. The timezone is injected (rather than read
// from the ambient local zone) so the axis is deterministic and testable across zones.
import {
  type ZonedDateTime,
  fromAbsolute,
  getLocalTimeZone,
  startOfMonth,
  startOfWeek
} from '@internationalized/date'

import { isoDate, pad2, shortWeekday } from '@/graphing/utils/timeFormat'

import type { TimeRange } from '../types'

export function timestampAt(timeRange: TimeRange, i: number): number {
  return timeRange.start + i * timeRange.step
}

export function sampleCount(timeRange: TimeRange): number {
  return Math.round((timeRange.end - timeRange.start) / timeRange.step) + 1
}

const SECONDS_PER_DAY = 86_400

export interface TimeAxisTick {
  position: number
  text: string | null
  lineWidth: number
}

interface Labelling {
  format: string
  labelSize: number
  labelShift: number
  labelDistanceAtLeast: number
}

function pickLabelling(start: ZonedDateTime, end: ZonedDateTime, timeRangeDays: number): Labelling {
  const sameYear = start.year === end.year
  const sameMonth = sameYear && start.month === end.month
  const sameDate = sameMonth && start.day === end.day

  if (sameDate) {
    return { format: '%H:%M', labelSize: 5, labelShift: 0, labelDistanceAtLeast: 0 }
  }
  if (timeRangeDays < 7) {
    return { format: '%a %H:%M', labelSize: 9, labelShift: 0, labelDistanceAtLeast: 0 }
  }
  if (timeRangeDays < 32 && sameMonth) {
    return {
      format: '%d',
      labelSize: 2.5,
      labelShift: SECONDS_PER_DAY / 2,
      labelDistanceAtLeast: SECONDS_PER_DAY
    }
  }
  if (sameYear) {
    return { format: '%m-%d', labelSize: 5, labelShift: 0, labelDistanceAtLeast: 0 }
  }
  return { format: '%Y-%m-%d', labelSize: 8, labelShift: 0, labelDistanceAtLeast: 0 }
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
  timeRange: number,
  widthEx: number,
  labelSize: number,
  labelDistanceAtLeast: number
): (start: ZonedDateTime, end: ZonedDateTime) => ZonedDateTime[] {
  const numLabels = Math.max(Math.floor((widthEx - 7) / labelSize), 2)
  const minDistance = Math.max(labelDistanceAtLeast, timeRange / numLabels)

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
  widthEx: number,
  step: number,
  timeZone: string = getLocalTimeZone()
): TimeAxisTick[] {
  startTime += step
  endTime -= step

  const timeRange = endTime - startTime
  if (timeRange <= 0) {
    return []
  }
  const safeWidthEx = Math.max(widthEx, 8)

  const startZoned = fromAbsolute(startTime * 1000, timeZone)
  const endZoned = fromAbsolute(endTime * 1000, timeZone)
  const timeRangeDays = timeRange / SECONDS_PER_DAY

  const labelling = pickLabelling(startZoned, endZoned, timeRangeDays)
  const producer = selectTickProducer(
    timeRange,
    safeWidthEx,
    labelling.labelSize,
    labelling.labelDistanceAtLeast
  )

  const ticks: TimeAxisTick[] = []
  const secondsPerChar = timeRange / (safeWidthEx - 7)
  for (const positionZoned of producer(startZoned, endZoned)) {
    let lineWidth = 2
    let position = Math.round(positionZoned.toDate().getTime() / 1000)
    let label: string | null = formatLabel(labelling.format, positionZoned)

    if (labelling.labelShift) {
      ticks.push({ position, text: null, lineWidth })
      lineWidth = 0
      position += labelling.labelShift
    }

    if (label !== null && (label.length / 3.5) * secondsPerChar > endTime - position) {
      label = null
    }
    ticks.push({ position, text: label, lineWidth })
  }
  return ticks
}
