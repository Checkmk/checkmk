/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { binEdges, binStart, drawnBinEdges, foldIntoBins, gridStep } from '@/graphing/utils/bins'

import {
  BIN_UNITS,
  HOUR,
  LOCAL_TIME_CASES,
  MINUTE,
  PLANNED_GRID,
  SERVED_GRIDS,
  WINDOW_SHAPES,
  expectedBinEdges,
  gridValuesReaching,
  offsetAt,
  ones,
  servedGrid,
  windowAround
} from './localTimeCases'

function utc(day: number, hour: number, minute = 0, month = 3): number {
  return Date.UTC(2026, month - 1, day, hour, minute) / 1000
}

function widths(edges: number[]): number[] {
  return edges.slice(1).map((edge, index) => edge - edges[index]!)
}

describe('binEdges', () => {
  it('ends on the interval end when the end is a bin edge', () => {
    const edges = binEdges('hour', { start: utc(10, 0), end: utc(10, 2) }, 'UTC')

    expect(edges).toEqual([utc(10, 0), utc(10, 1), utc(10, 2)])
  })

  it('ends with the bin that holds a partial end', () => {
    const edges = binEdges('hour', { start: utc(10, 0), end: utc(10, 1, 20) }, 'UTC')

    expect(edges).toEqual([utc(10, 0), utc(10, 1), utc(10, 2)])
  })

  it('opens one more bin for an end one second after a bin edge', () => {
    const edges = binEdges('hour', { start: utc(10, 0), end: utc(10, 2) + 1 }, 'UTC')

    expect(edges).toEqual([utc(10, 0), utc(10, 1), utc(10, 2), utc(10, 3)])
  })
})

const CASES_PER_BIN_UNIT = BIN_UNITS.flatMap((unit) =>
  LOCAL_TIME_CASES.map((localTimeCase) => ({ unit, ...localTimeCase }))
)

describe('local time cases', () => {
  it.each(LOCAL_TIME_CASES.filter(({ change }) => change !== null))(
    'change the offset at their instant: $name',
    ({ timeZone, instant }) => {
      expect(offsetAt(instant - 1, timeZone)).not.toBe(offsetAt(instant, timeZone))
    }
  )

  it.each(LOCAL_TIME_CASES.filter(({ change }) => change === null))(
    'keep one offset over their day window: $name',
    ({ timeZone, instant }) => {
      const window = windowAround('day', instant)

      expect(offsetAt(window.start, timeZone)).toBe(offsetAt(window.end, timeZone))
    }
  )
})

describe.each(WINDOW_SHAPES)('binEdges over $name', (shape) => {
  it.each(CASES_PER_BIN_UNIT)(
    'starts every $unit bin where the local clock starts it: $name',
    ({ unit, timeZone, instant }) => {
      const window = shape.window(unit, timeZone, instant)

      expect(binEdges(unit, window, timeZone)).toEqual(expectedBinEdges(unit, timeZone, window))
    }
  )
})

describe('binStart', () => {
  it.each(
    CASES_PER_BIN_UNIT.filter(({ change }) => change !== null).flatMap((localTimeCase) => [
      { ...localTimeCase, side: 'before', time: localTimeCase.instant - 5 * MINUTE },
      { ...localTimeCase, side: 'after', time: localTimeCase.instant + 5 * MINUTE }
    ])
  )(
    'starts the $unit bin $side the instant where the local clock starts it: $name',
    ({ unit, timeZone, time }) => {
      expect(binStart(unit, time, timeZone)).toBe(
        expectedBinEdges(unit, timeZone, { start: time, end: time + 1 })[0]
      )
    }
  )
})

describe('gridStep', () => {
  it.each(CASES_PER_BIN_UNIT)(
    'takes the coarsest step that meets every $unit edge: $name',
    ({ unit, timeZone, instant, gridStep: expected }) => {
      const edges = binEdges(unit, windowAround(unit, instant), timeZone)

      expect(gridStep(edges)).toBe(expected)
    }
  )

  it('takes quarter hours when no quarter-hour grid reaches every edge', () => {
    expect(gridStep([0, 600])).toBe(900)
  })
})

function groupedAtShift(change: 'forward' | 'back') {
  return LOCAL_TIME_CASES.filter((localTimeCase) => localTimeCase.change === change).flatMap(
    (localTimeCase) => [48, 120].map((plotWidth) => ({ ...localTimeCase, plotWidth }))
  )
}

function innerGroupLengths(edges: number[]): number[] {
  return widths(edges).slice(1, -1)
}

function mostCommon(values: number[]): number {
  const counts = new Map<number, number>()
  values.forEach((value) => counts.set(value, (counts.get(value) ?? 0) + 1))
  return [...counts].sort(([, a], [, b]) => b - a)[0]![0]
}

describe('drawnBinEdges', () => {
  const twoDays = { start: utc(10, 0), end: utc(12, 0) }

  it('keeps every bin that is wide enough to draw', () => {
    expect(drawnBinEdges('hour', twoDays, 480, 'UTC')).toEqual(binEdges('hour', twoDays, 'UTC'))
  })

  it('merges narrow hour bins into groups that start at multiples of the group size', () => {
    const edges = drawnBinEdges('hour', twoDays, 48, 'UTC')

    expect(widths(edges)).toEqual(Array.from({ length: 16 }, () => 3 * HOUR))
    expect(edges.every((edge) => (edge / HOUR) % 3 === 0)).toBe(true)
  })

  it('keeps the grouping when the interval moves by one bin', () => {
    const moved = { start: twoDays.start + HOUR, end: twoDays.end + HOUR }

    const edges = drawnBinEdges('hour', twoDays, 48, 'UTC')
    const movedEdges = drawnBinEdges('hour', moved, 48, 'UTC')

    expect(movedEdges.slice(1, -1)).toEqual(edges.slice(1))
  })

  it('cuts the outer groups at the bin edges of the interval', () => {
    const moved = { start: twoDays.start + HOUR, end: twoDays.end + HOUR }

    const edges = drawnBinEdges('hour', moved, 48, 'UTC')

    expect(widths(edges)).toEqual([2 * HOUR, ...Array.from({ length: 15 }, () => 3 * HOUR), HOUR])
  })

  it.each(groupedAtShift('back'))(
    'draws no inner hour group shorter than the others when the clocks go back: $name, $plotWidth px',
    ({ timeZone, instant, plotWidth }) => {
      const groups = innerGroupLengths(
        drawnBinEdges('hour', windowAround('hour', instant), plotWidth, timeZone)
      )

      expect(Math.min(...groups)).toBe(mostCommon(groups))
    }
  )

  it.each(groupedAtShift('forward'))(
    'shortens an inner hour group by at most the skipped hour when the clocks go forward: $name, $plotWidth px',
    ({ timeZone, instant, plotWidth }) => {
      const groups = innerGroupLengths(
        drawnBinEdges('hour', windowAround('hour', instant), plotWidth, timeZone)
      )

      expect(Math.min(...groups)).toBeGreaterThanOrEqual(mostCommon(groups) - HOUR)
    }
  )

  it('merges day bins on local calendar days', () => {
    const edges = drawnBinEdges('day', { start: utc(1, 12), end: utc(29, 12) }, 28, 'Europe/Berlin')

    expect(
      edges
        .slice(1, -1)
        .every((edge) => (edge + HOUR) % 86_400 === 0 || (edge + 2 * HOUR) % 86_400 === 0)
    ).toBe(true)
    expect(edges.length).toBeLessThan(29)
  })
})

describe('foldIntoBins', () => {
  it('sums the grid values of each bin', () => {
    const bins = foldIntoBins(
      [1, 2, null, 3, 4, 0, 0, 0],
      { start: 0, end: 7200, step: 900 },
      [0, 3600, 7200],
      'sum'
    )

    expect(bins).toEqual([
      { start: 0, end: 3600, value: 6 },
      { start: 3600, end: 7200, value: 4 }
    ])
  })

  it('leaves a bin without data empty instead of zero', () => {
    const bins = foldIntoBins(
      [null, null, 0, 0],
      { start: 0, end: 7200, step: 1800 },
      [0, 3600, 7200],
      'sum'
    )

    expect(bins.map((bin) => bin.value)).toEqual([null, 0])
  })

  it('leaves a bin past the served data empty', () => {
    const bins = foldIntoBins([1, 1], { start: 0, end: 1800, step: 900 }, [0, 3600, 7200], 'sum')

    expect(bins.map((bin) => bin.value)).toEqual([2, null])
  })

  it('ignores grid values outside the edges', () => {
    const bins = foldIntoBins([5, 1, 1, 5], { start: -900, end: 2700, step: 900 }, [0, 1800], 'sum')

    expect(bins.map((bin) => bin.value)).toEqual([2])
  })

  it('merges the bins that a coarser grid does not separate', () => {
    const bins = foldIntoBins(
      [1, 2],
      { start: 0, end: 7200, step: 3600 },
      [0, 1800, 3600, 5400, 7200],
      'sum'
    )

    expect(bins).toEqual([
      { start: 0, end: 3600, value: 1 },
      { start: 3600, end: 7200, value: 2 }
    ])
  })

  it('counts a grid value in the bin that holds most of it', () => {
    const bins = foldIntoBins([1, 2], { start: 0, end: 7200, step: 3600 }, [0, 3000, 7200], 'sum')

    expect(bins.map((bin) => bin.value)).toEqual([1, 2])
  })

  it('moves an inner edge halfway between two grid edges to the later one', () => {
    const bins = foldIntoBins([1, 1, 1], { start: 0, end: 1800, step: 600 }, [0, 900, 1800], 'sum')

    expect(bins.map((bin) => [bin.start, bin.end])).toEqual([
      [0, 1200],
      [1200, 1800]
    ])
  })

  it('reaches the first bin back to the grid edge before the first edge', () => {
    const bins = foldIntoBins([1, 1, 1], { start: 0, end: 1800, step: 600 }, [900, 1800], 'sum')

    expect(bins).toEqual([{ start: 600, end: 1800, value: 2 }])
  })

  it('reaches the last bin out to the grid edge after the last edge', () => {
    const bins = foldIntoBins([1, 1, 1], { start: 0, end: 1800, step: 600 }, [0, 900], 'sum')

    expect(bins).toEqual([{ start: 0, end: 1200, value: 2 }])
  })

  it('folds a coarse grid value into one bin when every edge lies inside it', () => {
    const sixHours = { start: utc(10, 18), end: utc(11, 0), step: 6 * HOUR }

    const bins = foldIntoBins([7], sixHours, [utc(10, 18), utc(10, 19), utc(10, 20)], 'sum')

    expect(bins).toEqual([{ start: utc(10, 18), end: utc(11, 0), value: 7 }])
  })
})

describe.each(SERVED_GRIDS)('foldIntoBins on a $name', (grid) => {
  function fold(unit: 'hour' | 'day', timeZone: string, instant: number) {
    const edges = binEdges(unit, windowAround(unit, instant), timeZone)
    const served = servedGrid(grid, { start: edges[0]!, end: edges.at(-1)! }, gridStep(edges))
    return { edges, served, bins: foldIntoBins(ones(served), served, edges, 'sum') }
  }

  it.each(CASES_PER_BIN_UNIT)('covers the $unit edges: $name', ({ unit, timeZone, instant }) => {
    const { edges, bins } = fold(unit, timeZone, instant)

    expect([bins[0]!.start <= edges[0]!, bins.at(-1)!.end >= edges.at(-1)!]).toEqual([true, true])
  })

  it.each(CASES_PER_BIN_UNIT)(
    'counts every grid value that reaches into the $unit edges once: $name',
    ({ unit, timeZone, instant }) => {
      const { edges, served, bins } = fold(unit, timeZone, instant)

      expect(bins.reduce((total, bin) => total + (bin.value ?? 0), 0)).toBe(
        gridValuesReaching(served, { start: edges[0]!, end: edges.at(-1)! })
      )
    }
  )

  it.each(CASES_PER_BIN_UNIT)(
    'keeps every inner $unit bin edge within half a step of an edge: $name',
    ({ unit, timeZone, instant }) => {
      const { edges, served, bins } = fold(unit, timeZone, instant)

      expect(
        bins
          .slice(1)
          .every((bin) =>
            edges.slice(1, -1).some((edge) => Math.abs(bin.start - edge) <= served.step / 2)
          )
      ).toBe(true)
    }
  )
})

describe('foldIntoBins on a planned grid', () => {
  it.each(CASES_PER_BIN_UNIT)(
    'draws every $unit bin on its edges: $name',
    ({ unit, timeZone, instant }) => {
      const edges = binEdges(unit, windowAround(unit, instant), timeZone)
      const served = servedGrid(
        PLANNED_GRID,
        { start: edges[0]!, end: edges.at(-1)! },
        gridStep(edges)
      )

      const bins = foldIntoBins(ones(served), served, edges, 'sum')

      expect([bins[0]!.start, ...bins.map((bin) => bin.end)]).toEqual(edges)
    }
  )
})
