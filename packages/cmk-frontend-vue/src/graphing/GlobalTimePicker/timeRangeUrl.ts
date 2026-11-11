/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate, getLocalTimeZone } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, computed } from 'vue'

import { type TimeStart, useGlobalRefresh, useGlobalTimeRange } from './globalTimeState'
import { durationSeconds, isRolling } from './private/timeRange'

/** The URL variables that carry a time range, as Grafana names them. */
export const TIME_RANGE_VARIABLES = ['from', 'to'] as const

/** A time range in URL variables: epoch milliseconds, or `now-<seconds>s` up to `now`. */
export type TimeRangeVariables = Record<(typeof TIME_RANGE_VARIABLES)[number], string>

const NOW = 'now'
const ROLLING_FROM = /^now-([1-9]\d*)s$/
const EPOCH_MS = /^\d+$/

/** The variables that carry `range` as its two instants in epoch milliseconds. */
export function fixedTimeRangeVariables(range: DateTimeRange): TimeRangeVariables {
  return {
    from: String(range.from.toDate().getTime()),
    to: String(range.to.toDate().getTime())
  }
}

/** The variables that carry `range` along a link; a live rolling range travels as its duration. */
export function linkTimeRangeVariables(range: DateTimeRange, live: boolean): TimeRangeVariables {
  if (live && isRolling(range)) {
    return { from: `now-${Math.round(durationSeconds(range))}s`, to: NOW }
  }
  return fixedTimeRangeVariables(range)
}

function validDate(epochMs: number): Date | null {
  const date = new Date(epochMs)
  return Number.isNaN(date.getTime()) ? null : date
}

function instant(value: string): Date | null {
  return EPOCH_MS.test(value) ? validDate(Number(value)) : null
}

/** How a page starts: from the time range a link carried in `url`, else from its own default. */
export function timeStartFromUrl(url: URL, live: boolean): TimeStart {
  const from = url.searchParams.get('from')
  const to = url.searchParams.get('to')
  if (from === null || to === null) {
    return { type: 'page_default', live }
  }

  const rolling = ROLLING_FROM.exec(from)
  if (rolling !== null && to === NOW) {
    const seconds = Number(rolling[1])
    return validDate(Date.now() - seconds * 1000) === null
      ? { type: 'page_default', live }
      : { type: 'linked_rolling', seconds, live }
  }

  const start = instant(from)
  const end = instant(to)
  if (start !== null && end !== null && start.getTime() < end.getTime()) {
    const zone = getLocalTimeZone()
    return { type: 'linked_fixed', range: { from: fromDate(start, zone), to: fromDate(end, zone) } }
  }
  return { type: 'page_default', live }
}

/** The variables that carry the page's time range; a live rolling range travels as its duration. */
export function useTimeRangeVariables(): ComputedRef<TimeRangeVariables | null> {
  const { activeTimeRange } = useGlobalTimeRange()
  const { refreshPaused } = useGlobalRefresh()
  return computed((previous) => {
    const range = activeTimeRange.value
    if (range === null) {
      return null
    }
    const variables = linkTimeRangeVariables(range, !refreshPaused.value)
    return previous?.from === variables.from && previous.to === variables.to ? previous : variables
  })
}
