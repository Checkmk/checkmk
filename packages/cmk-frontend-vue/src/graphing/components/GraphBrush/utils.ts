/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromAbsolute, getLocalTimeZone } from '@internationalized/date'

import { isoDate, pad2 } from '@/graphing/utils/timeFormat'

const zonedTime = (unixSeconds: number, timeZone: string) =>
  fromAbsolute(unixSeconds * 1000, timeZone)
const fmtDate = (unixSeconds: number, timeZone: string) => isoDate(zonedTime(unixSeconds, timeZone))
const fmtTime = (unixSeconds: number, timeZone: string) => {
  const zoned = zonedTime(unixSeconds, timeZone)
  return `${pad2(zoned.hour)}:${pad2(zoned.minute)}`
}

export function formatOverviewExtent(
  domain: { start: number; end: number },
  timeZone: string = getLocalTimeZone()
): string {
  const { start, end } = domain
  if (fmtDate(start, timeZone) === fmtDate(end, timeZone)) {
    return `${fmtDate(start, timeZone)} ${fmtTime(start, timeZone)}–${fmtTime(end, timeZone)}`
  }
  return `${fmtDate(start, timeZone)} — ${fmtDate(end, timeZone)}`
}

export interface WindowPreview {
  date: string
  time: string
}

export function formatWindowPreview(
  window: { start: number; end: number },
  timeZone: string = getLocalTimeZone()
): WindowPreview {
  const startDate = fmtDate(window.start, timeZone)
  const endDate = fmtDate(window.end, timeZone)
  return {
    date: startDate === endDate ? startDate : `${startDate} — ${endDate}`,
    time: `${fmtTime(window.start, timeZone)}–${fmtTime(window.end, timeZone)}`
  }
}
