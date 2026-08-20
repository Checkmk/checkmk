/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { timestampAt } from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'
import { drawnTimeRange, withEdgeNeighbours } from '@/graphing/utils/timeRange'

describe('withEdgeNeighbours', () => {
  const WINDOW = { start: 1_000_020, end: 1_000_620, step: 60 }

  test('asks for a sample past the end of the window it will be drawn over', () => {
    const window = WINDOW

    const fetched = withEdgeNeighbours(window)

    expect(fetched.end).toBeGreaterThan(window.end)
  })

  test('asks far enough back that its first sample falls before the window starts', () => {
    const window = WINDOW
    const firstValueIndex = 0

    const fetched = withEdgeNeighbours(window)

    expect(timestampAt(fetched, firstValueIndex)).toBeLessThan(window.start)
  })

  test('leaves the resolution the window resolved untouched', () => {
    const window = WINDOW

    const fetched = withEdgeNeighbours(window)

    expect(fetched.step).toBe(window.step)
  })
})

describe('drawnTimeRange', () => {
  const STEP = 60
  const GRID_BOUNDARY_BEFORE_START = 1_000_020
  const NEWEST_GRID_BOUNDARY_COVERED = 1_000_620

  test('snaps a window ending mid-interval back onto the data grid', () => {
    const endingMidInterval = { start: 1_000_037, end: 1_000_637 }
    const served = { start: 1_000_020, end: 1_000_740, step: STEP }

    const drawn = drawnTimeRange(endingMidInterval, served)

    expect(drawn.start).toBe(GRID_BOUNDARY_BEFORE_START)
    expect(drawn.end).toBe(NEWEST_GRID_BOUNDARY_COVERED)
  })

  test('leaves a window that already sits on the grid alone', () => {
    const onGrid = { start: GRID_BOUNDARY_BEFORE_START, end: NEWEST_GRID_BOUNDARY_COVERED }
    const served = { start: 1_000_020, end: 1_000_680, step: STEP }

    const drawn = drawnTimeRange(onGrid, served)

    expect(drawn.start).toBe(GRID_BOUNDARY_BEFORE_START)
    expect(drawn.end).toBe(NEWEST_GRID_BOUNDARY_COVERED)
  })

  test('keeps the span an exact multiple of the step', () => {
    const bothEndsMidInterval = { start: 1_000_037, end: 1_000_659 }
    const served = { start: 1_000_020, end: 1_000_740, step: STEP }

    const drawn = drawnTimeRange(bothEndsMidInterval, served)

    expect((drawn.end - drawn.start) % drawn.step).toBe(0)
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
