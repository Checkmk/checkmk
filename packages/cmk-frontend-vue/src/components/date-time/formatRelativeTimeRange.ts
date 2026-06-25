/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'

import { formatTime, zonedToParts } from './dateTimeUtils'
import type { ResolvedDateTimeSettings } from './types'

type RangeSettings = Pick<ResolvedDateTimeSettings, 'timeZone' | 'hourCycle' | 'formatLongDate'>

/**
 * Format the absolute "start – end" range for a relative duration ending at `end`.
 * Same-day ranges show times only; ranges that span days include the date.
 */
export function formatRelativeTimeRange(
  end: Date,
  durationSeconds: number,
  settings: RangeSettings
): string {
  const start = new Date(end.getTime() - durationSeconds * 1000)
  const startParts = zonedToParts(fromDate(start, settings.timeZone))
  const endParts = zonedToParts(fromDate(end, settings.timeZone))
  const startTime = formatTime(startParts.time, settings.hourCycle)
  const endTime = formatTime(endParts.time, settings.hourCycle)
  if (startParts.date.compare(endParts.date) === 0) {
    return `${startTime} – ${endTime}`
  }
  return `${settings.formatLongDate(startParts.date)}, ${startTime} – ${settings.formatLongDate(endParts.date)}, ${endTime}`
}
