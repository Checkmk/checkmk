/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { MIN_ZOOM_SAMPLES, MIN_ZOOM_TIME_RANGE_SECONDS } from '@/graphing/components/constants'
import { binnedTimeAxis, drawnTimeRange, minZoomSpan } from '@/graphing/utils/timeRange'

import { HOUR } from './localTimeCases'

describe('drawnTimeRange', () => {
  const STEP = 60
  const NEWEST_GRID_BOUNDARY_COVERED = 1_000_620
  const SERVED = { start: 1_000_020, end: 1_000_740, step: STEP }
  const LONG_AFTER_EVERY_WINDOW = 2_000_000

  test('draws a window that closed before the newest sample as it was requested', () => {
    const bothEndsMidInterval = { start: 1_000_037, end: 1_000_637 }

    const drawn = drawnTimeRange(bothEndsMidInterval, SERVED, LONG_AFTER_EVERY_WINDOW)

    expect(drawn.start).toBe(bothEndsMidInterval.start)
    expect(drawn.end).toBe(bothEndsMidInterval.end)
  })

  test('ends a window reaching into the still open interval on the newest closed sample', () => {
    const endingNow = { start: 1_000_037, end: 1_000_637 }
    const now = endingNow.end

    const drawn = drawnTimeRange(endingNow, SERVED, now)

    expect(drawn.end).toBe(NEWEST_GRID_BOUNDARY_COVERED)
  })

  test('keeps a window lying inside the still open interval drawable', () => {
    const insideTheOpenInterval = { start: 1_000_637, end: 1_000_659 }
    const now = insideTheOpenInterval.end

    const drawn = drawnTimeRange(insideTheOpenInterval, SERVED, now)

    expect(drawn.end).toBeGreaterThan(drawn.start)
  })

  test('holds the end inside the range the fetch answered with', () => {
    const reachingBeyondTheServedRange = { start: 0, end: 1_000_000 }
    const servedOneHourAtOneHourStep = { start: 0, end: 3_600, step: 3_600 }

    const drawn = drawnTimeRange(reachingBeyondTheServedRange, servedOneHourAtOneHourStep)

    expect(drawn.end).toBe(servedOneHourAtOneHourStep.end)
  })

  test('bounds the end by the answered range, not by where values stop', () => {
    const window = { start: 1_000_020, end: 1_000_680 }
    const servedPastTheNewestValue = { start: 1_000_020, end: 1_000_680, step: STEP }

    const drawn = drawnTimeRange(window, servedPastTheNewestValue)

    expect(drawn.end).toBe(servedPastTheNewestValue.end)
  })

  test('passes the window through when the step is unusable', () => {
    const window = { start: 500, end: 900 }
    const servedWithoutStep = { start: 0, end: 1_000, step: 0 }

    const drawn = drawnTimeRange(window, servedWithoutStep)

    expect(drawn.start).toBe(window.start)
    expect(drawn.end).toBe(window.end)
  })
})

describe('minZoomSpan', () => {
  test.each([
    ['no fetch has resolved a step', undefined],
    ['the resolved step is unusable', { start: 0, end: 1_000, step: 0 }]
  ])('is the configured minimum while %s', (_case, served) => {
    const span = minZoomSpan(served)

    expect(span).toBe(MIN_ZOOM_TIME_RANGE_SECONDS)
  })

  test('stays at the configured minimum at the resolution it was configured for', () => {
    const servedAtBaseResolution = {
      start: 0,
      end: 3_600,
      step: MIN_ZOOM_TIME_RANGE_SECONDS / MIN_ZOOM_SAMPLES
    }

    const span = minZoomSpan(servedAtBaseResolution)

    expect(span).toBe(MIN_ZOOM_TIME_RANGE_SECONDS)
  })

  test('keeps a window at a coarse resolution wide enough to hold its samples', () => {
    const servedSixHourly = { start: 0, end: 864_000, step: 21_600 }

    const span = minZoomSpan(servedSixHourly)

    expect(span / servedSixHourly.step).toBeGreaterThanOrEqual(MIN_ZOOM_SAMPLES)
  })
})

describe('binnedTimeAxis', () => {
  const TEN_THIRTY_SEVEN = Date.UTC(2026, 0, 1, 10, 37) / 1000
  const LAST_FOUR_HOURS = { start: TEN_THIRTY_SEVEN - 4 * HOUR, end: TEN_THIRTY_SEVEN }
  const SERVED = {
    start: Date.UTC(2026, 0, 1, 5) / 1000,
    end: Date.UTC(2026, 0, 1, 11) / 1000,
    step: HOUR
  }

  test('fetches whole local bins, the open one included', () => {
    const window = binnedTimeAxis('hour', 'UTC').planFetchWindow(LAST_FOUR_HOURS, 750)

    expect(window).toEqual({
      start: Date.UTC(2026, 0, 1, 6) / 1000,
      end: Date.UTC(2026, 0, 1, 11) / 1000,
      step: HOUR
    })
  })

  test('fetches on the step that meets the local bin edges', () => {
    const window = binnedTimeAxis('hour', 'Asia/Kathmandu').planFetchWindow(LAST_FOUR_HOURS, 750)

    expect(window).toEqual({
      start: Date.UTC(2026, 0, 1, 6, 15) / 1000,
      end: Date.UTC(2026, 0, 1, 11, 15) / 1000,
      step: 900
    })
  })

  test('draws up to the requested end, inside the last bin', () => {
    const drawn = binnedTimeAxis('hour', 'UTC').drawnTimeRange(LAST_FOUR_HOURS, SERVED)

    expect(drawn.end).toBe(TEN_THIRTY_SEVEN)
  })

  test('draws on the served step', () => {
    const drawn = binnedTimeAxis('hour', 'UTC').drawnTimeRange(LAST_FOUR_HOURS, SERVED)

    expect(drawn.step).toBe(HOUR)
  })

  test('draws a window shorter than the served step from its bin start', () => {
    const requested = {
      start: Date.UTC(2026, 0, 1, 21, 30) / 1000,
      end: Date.UTC(2026, 0, 1, 22, 30) / 1000
    }
    const servedSixHourly = {
      start: Date.UTC(2026, 0, 1) / 1000,
      end: Date.UTC(2026, 0, 2) / 1000,
      step: 6 * HOUR
    }

    const drawn = binnedTimeAxis('hour', 'UTC').drawnTimeRange(requested, servedSixHourly)

    expect(drawn.start).toBe(Date.UTC(2026, 0, 1, 21) / 1000)
  })

  test('zooms no deeper than one bin, or than the host allows', () => {
    const axis = binnedTimeAxis('day', 'UTC')

    expect([axis.minSpan(null), axis.minSpan(2 * 86_400)]).toEqual([86_400, 2 * 86_400])
  })
})
