/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getLocalTimeZone, now } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'

/** The last `totalSeconds`, ending now (browser zone). */
export function rollingRange(totalSeconds: number): DateTimeRange {
  const to = now(getLocalTimeZone())
  return { from: to.subtract({ seconds: totalSeconds }), to }
}

/** Duration in seconds for the given time range. */
export function durationSeconds(range: DateTimeRange): number {
  return (range.to.toDate().getTime() - range.from.toDate().getTime()) / 1000
}

/** Whether the range ends within `toleranceSeconds` of now. */
export function endsNow(range: DateTimeRange, toleranceSeconds = 60): boolean {
  return Math.abs(range.to.toDate().getTime() - Date.now()) <= toleranceSeconds * 1000
}

/** Whether the range ends before now. Not the negation of `endsNow`: the calendar quick
 * ranges (Today, This week, …) end in the future and still cover the present.
 */
export function endsInThePast(range: DateTimeRange, toleranceSeconds = 60): boolean {
  return range.to.toDate().getTime() < Date.now() - toleranceSeconds * 1000
}

/** Whether a refresh should carry the range forward. Not `endsNow`: a window that fell behind
 * while unrefreshed is caught up on resume. A calendar quick range (Today, This week) reaches into
 * the future and is left alone - re-rolling it would turn an absolute window into a relative one.
 */
export function isRolling(range: DateTimeRange): boolean {
  return range.to.toDate().getTime() <= Date.now()
}
