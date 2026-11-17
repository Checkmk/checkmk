/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { timestampAt } from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'
import { MIN_ZOOM_SAMPLES, MIN_ZOOM_TIME_RANGE_SECONDS } from '@/graphing/components/constants'
import { drawnBinEdges, foldIntoBins } from '@/graphing/utils/bins'
import { binnedTimeAxis, continuousTimeAxis, drawnTimeRange } from '@/graphing/utils/timeRange'

import { HOUR, SIX_HOUR_GRID, type ServedGrid, ones, servedGrid } from './localTimeCases'

describe('drawnTimeRange', () => {
  const STEP = 60
  const ONE_MINUTE = 60
  const SERVED = { start: 1_000_020, end: 1_000_740, step: STEP }
  const LONG_AFTER_EVERY_WINDOW = 2_000_000

  test('draws a window that closed before the newest sample as it was requested', () => {
    const bothEndsMidInterval = {
      start: 1_000_037,
      end: 1_000_637,
      requestedAt: LONG_AFTER_EVERY_WINDOW
    }

    const drawn = drawnTimeRange(bothEndsMidInterval, SERVED)

    expect(drawn.start).toBe(bothEndsMidInterval.start)
    expect(drawn.end).toBe(bothEndsMidInterval.end)
  })

  test('ends a window ending now on the newest sample a once-a-minute check has written', () => {
    const endingNow = { start: 1_000_037, end: 1_000_637, requestedAt: 1_000_637 }

    const drawn = drawnTimeRange(endingNow, SERVED)

    expect(drawn.end % STEP).toBe(0)
    expect(endingNow.requestedAt - drawn.end).toBeGreaterThanOrEqual(ONE_MINUTE)
    expect(endingNow.requestedAt - drawn.end).toBeLessThan(ONE_MINUTE + STEP)
  })

  test('ends a window ending now at a coarse step a minute back, not a whole step back', () => {
    const FIVE_MINUTES = 300
    const servedFiveMinutely = { start: 999_900, end: 1_003_800, step: FIVE_MINUTES }
    const endingMoreThanAMinuteIntoAStep = {
      start: 1_000_100,
      end: 1_003_400,
      requestedAt: 1_003_400
    }

    const drawn = drawnTimeRange(endingMoreThanAMinuteIntoAStep, servedFiveMinutely)

    expect(drawn.end % FIVE_MINUTES).toBe(0)
    expect(endingMoreThanAMinuteIntoAStep.requestedAt - drawn.end).toBeGreaterThanOrEqual(
      ONE_MINUTE
    )
    expect(endingMoreThanAMinuteIntoAStep.requestedAt - drawn.end).toBeLessThan(FIVE_MINUTES)
  })

  test('draws a window ending after it was requested up to the last grid point inside it', () => {
    const endingInTheFuture = { start: 1_000_037, end: 1_000_637, requestedAt: 1_000_300 }

    const drawn = drawnTimeRange(endingInTheFuture, SERVED)

    expect(drawn.end % STEP).toBe(0)
    expect(drawn.end).toBeGreaterThan(endingInTheFuture.requestedAt)
    expect(endingInTheFuture.end - drawn.end).toBeLessThan(STEP)
  })

  test('keeps a window ending now at the zoom floor as wide as it was requested', () => {
    const atTheZoomFloor = {
      start: 1_000_637 - MIN_ZOOM_TIME_RANGE_SECONDS,
      end: 1_000_637,
      requestedAt: 1_000_637
    }

    const drawn = drawnTimeRange(atTheZoomFloor, SERVED)

    expect(drawn.end - drawn.start).toBe(atTheZoomFloor.end - atTheZoomFloor.start)
  })

  test('keeps a window lying inside the still open interval drawable', () => {
    const insideTheOpenInterval = { start: 1_000_637, end: 1_000_659, requestedAt: 1_000_659 }

    const drawn = drawnTimeRange(insideTheOpenInterval, SERVED)

    expect(drawn.end).toBeGreaterThan(drawn.start)
  })

  test('holds the end inside the range the fetch answered with', () => {
    const reachingBeyondTheServedRange = {
      start: 0,
      end: 1_000_000,
      requestedAt: LONG_AFTER_EVERY_WINDOW
    }
    const servedOneHourAtOneHourStep = { start: 0, end: 3_600, step: 3_600 }

    const drawn = drawnTimeRange(reachingBeyondTheServedRange, servedOneHourAtOneHourStep)

    expect(drawn.end).toBe(servedOneHourAtOneHourStep.end)
  })

  test('bounds the end by the answered range, not by where values stop', () => {
    const window = { start: 1_000_020, end: 1_000_680, requestedAt: LONG_AFTER_EVERY_WINDOW }
    const servedPastTheNewestValue = { start: 1_000_020, end: 1_000_680, step: STEP }

    const drawn = drawnTimeRange(window, servedPastTheNewestValue)

    expect(drawn.end).toBe(servedPastTheNewestValue.end)
  })

  test('passes the window through when the step is unusable', () => {
    const window = { start: 500, end: 900, requestedAt: LONG_AFTER_EVERY_WINDOW }
    const servedWithoutStep = { start: 0, end: 1_000, step: 0 }

    const drawn = drawnTimeRange(window, servedWithoutStep)

    expect(drawn.start).toBe(window.start)
    expect(drawn.end).toBe(window.end)
  })
})

describe('the samples a continuous time axis draws', () => {
  const STEP = 60
  const SERVED = { start: 1_000_020, end: 1_000_740, step: STEP }

  function intervalOfSample(served: { start: number; step: number; end: number }, index: number) {
    const end = timestampAt(served, index)
    return { start: end - served.step, end }
  }

  test('run from the sample whose interval holds the start to the one holding the end', () => {
    const drawn = { start: 1_000_137, end: 1_000_437 }

    const samples = continuousTimeAxis().drawnSamples(drawn, SERVED)

    const first = intervalOfSample(SERVED, samples!.firstIndex)
    const last = intervalOfSample(SERVED, samples!.lastIndex)
    expect(drawn.start).toBeGreaterThan(first.start)
    expect(drawn.start).toBeLessThanOrEqual(first.end)
    expect(drawn.end).toBeGreaterThan(last.start)
    expect(drawn.end).toBeLessThanOrEqual(last.end)
  })

  test('hold the one sample a window inside a single interval lies in', () => {
    const SIX_HOURS = 21_600
    const servedSixHourly = { start: 0, end: 10 * SIX_HOURS, step: SIX_HOURS }
    const tenMinutesInsideOneStep = { start: 3 * SIX_HOURS + 1_000, end: 3 * SIX_HOURS + 1_600 }

    const samples = continuousTimeAxis().drawnSamples(tenMinutesInsideOneStep, servedSixHourly)

    expect(samples!.lastIndex).toBe(samples!.firstIndex)
  })

  test('are not placed without a usable step', () => {
    const servedWithoutStep = { start: 0, end: 1_000, step: 0 }

    const samples = continuousTimeAxis().drawnSamples({ start: 500, end: 900 }, servedWithoutStep)

    expect(samples).toBeNull()
  })
})

describe('the zoom floor of the continuous time axis', () => {
  const zoomFloor = continuousTimeAxis().zoomFloor

  test.each([
    ['no fetch has resolved a step', undefined],
    ['the resolved step is unusable', { start: 0, end: 1_000, step: 0 }]
  ])('is the configured minimum while %s', (_case, served) => {
    const span = zoomFloor(served)

    expect(span).toBe(MIN_ZOOM_TIME_RANGE_SECONDS)
  })

  test('stays at the configured minimum at the resolution it was configured for', () => {
    const servedAtBaseResolution = {
      start: 0,
      end: 3_600,
      step: MIN_ZOOM_TIME_RANGE_SECONDS / MIN_ZOOM_SAMPLES
    }

    const span = zoomFloor(servedAtBaseResolution)

    expect(span).toBe(MIN_ZOOM_TIME_RANGE_SECONDS)
  })

  test('keeps a window at a coarse resolution wide enough to hold its samples', () => {
    const servedSixHourly = { start: 0, end: 864_000, step: 21_600 }

    const span = zoomFloor(servedSixHourly)

    expect(span / servedSixHourly.step).toBeGreaterThanOrEqual(MIN_ZOOM_SAMPLES)
  })

  test('lets a time zoom reach the minimum of the host, whatever the data on screen', () => {
    const servedSixHourly = { start: 0, end: 864_000, step: 21_600 }

    expect(continuousTimeAxis().minSpan(MIN_ZOOM_TIME_RANGE_SECONDS, servedSixHourly)).toBe(
      MIN_ZOOM_TIME_RANGE_SECONDS
    )
  })
})

describe('binnedTimeAxis', () => {
  const TEN_THIRTY_SEVEN = Date.UTC(2026, 0, 1, 10, 37) / 1000
  const LAST_FOUR_HOURS = { start: TEN_THIRTY_SEVEN - 4 * HOUR, end: TEN_THIRTY_SEVEN }
  const LAST_FOUR_HOURS_ANSWERED = { ...LAST_FOUR_HOURS, requestedAt: TEN_THIRTY_SEVEN }
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
    const drawn = binnedTimeAxis('hour', 'UTC').drawnTimeRange(LAST_FOUR_HOURS_ANSWERED, SERVED)

    expect(drawn.end).toBe(TEN_THIRTY_SEVEN)
  })

  test('draws on the served step', () => {
    const drawn = binnedTimeAxis('hour', 'UTC').drawnTimeRange(LAST_FOUR_HOURS_ANSWERED, SERVED)

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

    const drawn = binnedTimeAxis('hour', 'UTC').drawnTimeRange(
      { ...requested, requestedAt: requested.end },
      servedSixHourly
    )

    expect(drawn.start).toBe(Date.UTC(2026, 0, 1, 21) / 1000)
  })

  // prettier-ignore
  test.each([
    { name: 'hour bins before a fetch has served a step', unit: 'hour' as const, step: null, floor: HOUR },
    { name: 'hour bins on the planned grid', unit: 'hour' as const, step: HOUR, floor: HOUR },
    { name: 'hour bins on a grid finer than a bin', unit: 'hour' as const, step: 15 * 60, floor: HOUR },
    { name: 'hour bins on a six-hour grid', unit: 'hour' as const, step: 6 * HOUR, floor: 6 * HOUR },
    { name: 'hour bins on a 90 min grid', unit: 'hour' as const, step: 90 * 60, floor: 2 * HOUR },
    { name: 'day bins on a six-hour grid', unit: 'day' as const, step: 6 * HOUR, floor: 24 * HOUR }
  ])('refuses a time zoom at whole bins that hold a served step, for $name', ({ unit, step, floor }) => {
    const served = step === null ? undefined : { start: 0, end: 100 * step, step }

    expect(binnedTimeAxis(unit, 'UTC').zoomFloor(served)).toBe(floor)
  })

  test('lets a time zoom reach the floor, or what the host allows', () => {
    const axis = binnedTimeAxis('hour', 'UTC')
    const servedSixHourly = { start: 0, end: 864_000, step: 6 * HOUR }

    expect([axis.minSpan(null, servedSixHourly), axis.minSpan(12 * HOUR, servedSixHourly)]).toEqual(
      [axis.zoomFloor(servedSixHourly), 12 * HOUR]
    )
  })
})

const PLOT_WIDTH = 750

function sumOf(values: number[]): number {
  return values.reduce((total, value) => total + value, 0)
}

function drawnBars(
  unit: 'hour' | 'day',
  timeZone: string,
  requested: { start: number; end: number },
  grid: ServedGrid
) {
  const axis = binnedTimeAxis(unit, timeZone)
  const planned = axis.planFetchWindow(requested, PLOT_WIDTH)
  const served = servedGrid(grid, planned, planned.step)
  const view = axis.drawnTimeRange({ ...requested, requestedAt: requested.end }, served)
  const edges = drawnBinEdges(unit, view, PLOT_WIDTH, timeZone)
  return { view, bins: foldIntoBins(ones(served), served, edges, 'sum') }
}

describe('the bars of a binned time axis', () => {
  test('cover a window shorter than the served step with one bar', () => {
    const requested = {
      start: Date.UTC(2026, 0, 1, 21, 30) / 1000,
      end: Date.UTC(2026, 0, 1, 22, 30) / 1000
    }
    const { bins } = drawnBars('hour', 'UTC', requested, SIX_HOUR_GRID)

    expect(bins).toEqual([
      { start: Date.UTC(2026, 0, 1, 18) / 1000, end: Date.UTC(2026, 0, 2) / 1000, value: 1 }
    ])
  })

  test('count in the legend exactly the samples the bars fold in', () => {
    const axis = binnedTimeAxis('hour', 'UTC')
    const requested = {
      start: Date.UTC(2026, 0, 1, 6, 37) / 1000,
      end: Date.UTC(2026, 0, 1, 10, 37) / 1000
    }
    const served = {
      start: Date.UTC(2026, 0, 1, 5) / 1000,
      end: Date.UTC(2026, 0, 1, 11) / 1000,
      step: HOUR
    }
    const distinctlySummingValues = ones(served).map((_one, index) => 2 ** index)
    const view = axis.drawnTimeRange({ ...requested, requestedAt: requested.end }, served)
    const bars = foldIntoBins(
      distinctlySummingValues,
      served,
      drawnBinEdges('hour', view, PLOT_WIDTH, 'UTC'),
      'sum'
    )

    const samples = axis.drawnSamples(view, served)

    const counted = distinctlySummingValues.slice(samples!.firstIndex, samples!.lastIndex + 1)
    expect(sumOf(counted)).toBe(sumOf(bars.map((bar) => bar.value ?? 0)))
  })
})
