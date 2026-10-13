/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { describe, expect, test } from 'vitest'

import { timestampAt } from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'
import { regionPath } from '@/graphing/components/TimeSeriesGraph/render/shadedRegions'
import type { ShadedRegion, TimeRange } from '@/graphing/components/TimeSeriesGraph/types'

const DATA_RANGE: TimeRange = { start: 0, end: 30, step: 10 }
const PLOT = { top: 0, bottom: 100 }
const xScale = ((date: Date) => date.getTime() / 1000) as unknown as ScaleTime<number, number>
const yScale = ((value: number) => 100 - value) as unknown as ScaleLinear<number, number>

function region(lower: (number | null)[] | null, upper: (number | null)[] | null): ShadedRegion {
  return {
    name: 'region-0',
    title: 'OK area',
    color: '#15d1a0',
    data_points: { lower, upper }
  }
}

describe('regionPath', () => {
  test('closes the area between the two bounds it is given', () => {
    const path = regionPath(region([10, 10], [20, 20]), DATA_RANGE, xScale, yScale, PLOT)

    expect(path).toBe('M10,80L20,80L20,90L10,90Z')
  })

  test('an absent upper bound runs to the top of the plot', () => {
    const path = regionPath(region([10, 10], null), DATA_RANGE, xScale, yScale, PLOT)

    expect(path).toBe(`M10,${PLOT.top}L20,${PLOT.top}L20,90L10,90Z`)
  })

  test('an absent lower bound runs to the bottom of the plot', () => {
    const path = regionPath(region(null, [20, 20]), DATA_RANGE, xScale, yScale, PLOT)

    expect(path).toBe(`M10,80L20,80L20,${PLOT.bottom}L10,${PLOT.bottom}Z`)
  })

  test('a gap in a bound leaves that point out rather than closing across it', () => {
    const path = regionPath(region([10, null, 10], [20, 20, 20]), DATA_RANGE, xScale, yScale, PLOT)

    expect(path).toBe('M10,80L30,80L30,90L10,90Z')
  })

  test('a region with no drawable point yields no path at all', () => {
    expect(regionPath(region([null], [null]), DATA_RANGE, xScale, yScale, PLOT)).toBe('')
  })

  test('places its points where the curves place theirs', () => {
    const path = regionPath(region([10, 10], [20, 20]), DATA_RANGE, xScale, yScale, PLOT)

    expect(path.startsWith(`M${timestampAt(DATA_RANGE, 0)},`)).toBe(true)
  })
})
