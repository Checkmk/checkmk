/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromAbsolute, getLocalTimeZone } from '@internationalized/date'
import { renderDate } from 'cmk-ui-library/lib/renderTime'

import { pad2 } from '@/graphing/utils/timeFormat'

const zonedTime = (unixSeconds: number, timeZone: string) =>
  fromAbsolute(unixSeconds * 1000, timeZone)
const fmtTime = (unixSeconds: number, timeZone: string) => {
  const zoned = zonedTime(unixSeconds, timeZone)
  return `${pad2(zoned.hour)}:${pad2(zoned.minute)}`
}

export function formatOverviewExtent(
  domain: { start: number; end: number },
  timeZone: string = getLocalTimeZone()
): string {
  const { date, time } = formatWindowPreview(domain, timeZone)
  return `${date} | ${time}`
}

export interface WindowPreview {
  date: string
  time: string
}

export function formatWindowPreview(
  window: { start: number; end: number },
  timeZone: string = getLocalTimeZone()
): WindowPreview {
  const startDate = renderDate(window.start, timeZone)
  const endDate = renderDate(window.end, timeZone)
  return {
    date: startDate === endDate ? startDate : `${startDate} — ${endDate}`,
    time: `${fmtTime(window.start, timeZone)}–${fmtTime(window.end, timeZone)}`
  }
}
