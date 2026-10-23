/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  deriveGrid,
  resampleOnGrid,
  samplingIntervalSecs
} from '@/maps/map/components/MetricChart/resample'
import type { MetricPoint } from '@/maps/types/api'

function series(...samples: [number, number][]): MetricPoint[] {
  return samples.map(([ts, value]) => ({ ts, value, unit: '' }))
}

describe('samplingIntervalSecs', () => {
  it('has no interval without at least two samples', () => {
    expect(samplingIntervalSecs([])).toBeNull()
    expect(samplingIntervalSecs([series([100, 1])])).toBeNull()
  })

  it('reports the gap between evenly polled samples', () => {
    expect(samplingIntervalSecs([series([100, 1], [160, 2], [220, 3])])).toBe(60)
  })

  it('takes the median, so one outage does not coarsen the whole grid', () => {
    const withGap = series([0, 1], [60, 2], [120, 3], [3720, 4], [3780, 5])
    expect(samplingIntervalSecs([withGap])).toBe(60)
  })

  it('pools the gaps of every series it is given', () => {
    expect(samplingIntervalSecs([series([0, 1], [30, 2]), series([0, 1], [30, 2])])).toBe(30)
  })
})

describe('deriveGrid', () => {
  it('resolves at the series own polling cadence', () => {
    const grid = deriveGrid([series([540, 1], [600, 2], [660, 3])], 600, 660)
    expect(grid.step).toBe(60)
    expect(grid.count).toBe(10)
    expect(grid.end - grid.start).toBe(600)
  })

  it('falls back to the window where nothing has been polled yet', () => {
    const grid = deriveGrid([[]], 600, 1000)
    expect(grid.step).toBeGreaterThan(0)
    expect(grid.count).toBeGreaterThan(0)
  })

  it('never resolves finer than the slot cap, however fast the polling', () => {
    const dense = series(...Array.from({ length: 50 }, (_unused, i): [number, number] => [i, i]))
    const grid = deriveGrid([dense], 36_000, 36_000)
    expect(grid.count).toBeLessThanOrEqual(600)
  })

  it('ends on a slot boundary, so successive renders share the same grid', () => {
    const grid = deriveGrid([series([0, 1], [60, 2])], 600, 1234)
    expect(grid.end % grid.step).toBe(0)
  })
})

describe('resampleOnGrid', () => {
  const grid = { start: 0, end: 300, step: 60, count: 5 }

  it('puts each sample in the slot it is nearest to', () => {
    expect(resampleOnGrid(series([0, 10], [60, 20], [120, 30]), grid)).toEqual([
      10,
      20,
      30,
      null,
      null
    ])
  })

  it('tolerates jitter around a slot', () => {
    expect(resampleOnGrid(series([5, 10], [55, 20]), grid)).toEqual([10, 20, null, null, null])
  })

  it('leaves a slot the connection has no sample for empty, rather than bridging it', () => {
    expect(resampleOnGrid(series([0, 10], [180, 40]), grid)).toEqual([10, null, null, 40, null])
  })

  it('averages samples that share a slot', () => {
    expect(resampleOnGrid(series([0, 10], [1, 20]), grid)[0]).toBe(15)
  })

  it('drops samples outside the window', () => {
    expect(resampleOnGrid(series([-600, 1], [6000, 2]), grid)).toEqual([
      null,
      null,
      null,
      null,
      null
    ])
  })
})
