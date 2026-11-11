/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  initGlobalTime,
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'
import { timeStartFromUrl, useTimeRangeVariables } from '@/graphing/GlobalTimePicker/timeRangeUrl'

const START_MS = Date.parse('2026-01-01T00:00:00Z')
const FOUR_HOURS_MS = 4 * 3600 * 1000

function rangeOf(fromMs: number, toMs: number): DateTimeRange {
  return { from: fromDate(new Date(fromMs), 'UTC'), to: fromDate(new Date(toMs), 'UTC') }
}

function pageUrl(query: string): URL {
  return new URL(`https://example.com/check_mk/dashboard.py?name=main&${query}`)
}

describe('timeStartFromUrl', () => {
  it('starts the duration a link carried, live as the page is', () => {
    expect(timeStartFromUrl(pageUrl('from=now-14400s&to=now'), true)).toEqual({
      type: 'linked_rolling',
      seconds: 14400,
      live: true
    })
  })

  it('starts the two instants a link carried', () => {
    const start = timeStartFromUrl(pageUrl(`from=${START_MS}&to=${START_MS + FOUR_HOURS_MS}`), true)

    expect(start.type).toBe('linked_fixed')
    expect(
      start.type === 'linked_fixed' && [
        start.range.from.toDate().getTime(),
        start.range.to.toDate().getTime()
      ]
    ).toEqual([START_MS, START_MS + FOUR_HOURS_MS])
  })

  it.each([
    ['no time range', 'host=web01'],
    ['only a start', 'from=now-14400s'],
    ['only an end', 'to=now'],
    ['a duration that does not end now', `from=now-14400s&to=${START_MS}`],
    ['a duration of nothing', 'from=now-0s&to=now'],
    ['words', 'from=yesterday&to=today'],
    ['an end before the start', `from=${START_MS + FOUR_HOURS_MS}&to=${START_MS}`],
    ['an end at the start', `from=${START_MS}&to=${START_MS}`],
    ['an instant beyond any date', `from=${START_MS}&to=99999999999999999999`],
    ['a duration beyond any date', 'from=now-99999999999999999999s&to=now']
  ])('starts from the page default for %s', (_case, query) => {
    expect(timeStartFromUrl(pageUrl(query), false)).toEqual({ type: 'page_default', live: false })
  })
})

describe('useTimeRangeVariables', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(START_MS + FOUR_HOURS_MS)
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
    vi.useRealTimers()
  })

  it('carries a live rolling range as its duration', () => {
    useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')
    useGlobalRefresh().resumeRefresh()

    expect(useTimeRangeVariables().value).toEqual({ from: 'now-14400s', to: 'now' })
  })

  it('carries a live rolling duration in whole seconds', () => {
    initGlobalTime({ intervalSeconds: null, start: { type: 'page_default', live: true } })
    useGlobalTimeRange().setActiveTimeRange(
      rangeOf(START_MS - 1600, START_MS + FOUR_HOURS_MS),
      'time_picker'
    )

    expect(useTimeRangeVariables().value?.from).toBe('now-14402s')
  })

  it('carries a paused range as its two instants', () => {
    useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')
    useGlobalRefresh().pauseRefresh()

    expect(useTimeRangeVariables().value).toEqual({
      from: String(START_MS),
      to: String(START_MS + FOUR_HOURS_MS)
    })
  })

  it('carries a live range that reaches into the future as its two instants', () => {
    const today = rangeOf(START_MS, START_MS + 6 * FOUR_HOURS_MS)
    useGlobalTimeRange().setActiveTimeRange(today, 'time_picker')
    useGlobalRefresh().resumeRefresh()

    expect(useTimeRangeVariables().value).toEqual({
      from: String(START_MS),
      to: String(START_MS + 6 * FOUR_HOURS_MS)
    })
  })

  it('carries nothing while the page has no range', () => {
    expect(useTimeRangeVariables().value).toBeNull()
  })
})
