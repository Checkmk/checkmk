/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getLocalTimeZone, now } from '@internationalized/date'

import type { DateTimeRange } from '@/components/date-time'

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
