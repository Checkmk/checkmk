/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'

import type { WidgetTimeRange } from '@/dashboard/types/widget'

import { widgetTimeRange } from './widgetTimeRange'

/** What a dashboard posts to the page of an iframe widget on load, on each range change and on each tick. */
export interface DashboardTimeRangeMessage {
  type: 'cmk:dashboard:time-range'
  range: WidgetTimeRange
  tick: number
}

export function dashboardTimeRangeMessage(
  range: DateTimeRange,
  tick: number
): DashboardTimeRangeMessage {
  return { type: 'cmk:dashboard:time-range', range: widgetTimeRange(range), tick }
}

/** Whether a received message is the dashboard's {@link DashboardTimeRangeMessage}. */
export function isDashboardTimeRangeMessage(data: unknown): data is DashboardTimeRangeMessage {
  if (typeof data !== 'object' || data === null) {
    return false
  }
  const { type, range, tick } = data as Record<string, unknown>
  if (type !== 'cmk:dashboard:time-range' || typeof tick !== 'number') {
    return false
  }
  if (typeof range !== 'object' || range === null) {
    return false
  }
  const { start, end } = range as Record<string, unknown>
  return typeof start === 'string' && typeof end === 'string'
}
