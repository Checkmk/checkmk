/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { MIN_ZOOM_SAMPLES, MIN_ZOOM_TIME_RANGE_SECONDS } from '@/graphing/components/constants'
import { drawnTimeRange, minZoomSpan } from '@/graphing/utils/timeRange'

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
