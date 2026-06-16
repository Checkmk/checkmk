/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromAbsolute, getDayOfWeek } from '@internationalized/date'
import { describe, expect, test } from 'vitest'

import {
  computeTimeAxis,
  sampleCount,
  timestampAt
} from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'

const BERLIN = 'Europe/Berlin'

describe('timestampAt', () => {
  test('returns the range start at index 0', () => {
    const range = { start: 1_700_000_000, end: 1_700_000_100, step: 10 }
    expect(timestampAt(range, 0)).toBe(1_700_000_000)
  })

  test('advances by one step per index', () => {
    const range = { start: 1_700_000_000, end: 1_700_000_100, step: 10 }
    expect(timestampAt(range, 5)).toBe(1_700_000_050)
  })
})

describe('sampleCount', () => {
  test('counts both bounds inclusively', () => {
    const range = { start: 1_700_000_000, end: 1_700_000_100, step: 10 }
    expect(sampleCount(range)).toBe(11)
  })
})

// The five band cases reuse the backend's exact inputs and expected ticks
// (tests/unit/cmk/gui/graphing/test_artwork.py::test_compute_graph_t_axis, Europe/Berlin),
// so a match proves the port reproduces the source tick-for-tick.
describe('computeTimeAxis label-format bands (Europe/Berlin, matches backend)', () => {
  test('labels a within-day (4h) range as HH:MM', () => {
    const ticks = computeTimeAxis(1668502320, 1668516720, 70, 60, BERLIN)
    expect(ticks).toEqual([
      { position: 1668502800, text: '10:00', lineWidth: 2 },
      { position: 1668504000, text: '10:20', lineWidth: 2 },
      { position: 1668505200, text: '10:40', lineWidth: 2 },
      { position: 1668506400, text: '11:00', lineWidth: 2 },
      { position: 1668507600, text: '11:20', lineWidth: 2 },
      { position: 1668508800, text: '11:40', lineWidth: 2 },
      { position: 1668510000, text: '12:00', lineWidth: 2 },
      { position: 1668511200, text: '12:20', lineWidth: 2 },
      { position: 1668512400, text: '12:40', lineWidth: 2 },
      { position: 1668513600, text: '13:00', lineWidth: 2 },
      { position: 1668514800, text: '13:20', lineWidth: 2 },
      { position: 1668516000, text: '13:40', lineWidth: 2 }
    ])
  })

  test('labels a sub-week (25h) range as weekday + time', () => {
    const ticks = computeTimeAxis(1668426600, 1668516600, 70, 300, BERLIN)
    expect(ticks).toEqual([
      { position: 1668438000, text: 'Mon 16:00', lineWidth: 2 },
      { position: 1668452400, text: 'Mon 20:00', lineWidth: 2 },
      { position: 1668466800, text: 'Tue 00:00', lineWidth: 2 },
      { position: 1668481200, text: 'Tue 04:00', lineWidth: 2 },
      { position: 1668495600, text: 'Tue 08:00', lineWidth: 2 },
      { position: 1668510000, text: 'Tue 12:00', lineWidth: 2 }
    ])
  })

  test('labels a within-month (8d) range as centered day-of-month', () => {
    const ticks = computeTimeAxis(1667826000, 1668517200, 70, 1800, BERLIN)
    expect(ticks).toEqual([
      { position: 1667862000, text: null, lineWidth: 2 },
      { position: 1667905200, text: '08', lineWidth: 0 },
      { position: 1667948400, text: null, lineWidth: 2 },
      { position: 1667991600, text: '09', lineWidth: 0 },
      { position: 1668034800, text: null, lineWidth: 2 },
      { position: 1668078000, text: '10', lineWidth: 0 },
      { position: 1668121200, text: null, lineWidth: 2 },
      { position: 1668164400, text: '11', lineWidth: 0 },
      { position: 1668207600, text: null, lineWidth: 2 },
      { position: 1668250800, text: '12', lineWidth: 0 },
      { position: 1668294000, text: null, lineWidth: 2 },
      { position: 1668337200, text: '13', lineWidth: 0 },
      { position: 1668380400, text: null, lineWidth: 2 },
      { position: 1668423600, text: '14', lineWidth: 0 },
      { position: 1668466800, text: null, lineWidth: 2 },
      { position: 1668510000, text: null, lineWidth: 0 }
    ])
  })

  test('labels a within-year (35d) range as MM-DD', () => {
    const ticks = computeTimeAxis(1665486000, 1668519000, 70, 9000, BERLIN)
    expect(ticks).toEqual([
      { position: 1665698400, text: '10-14', lineWidth: 2 },
      { position: 1665957600, text: '10-17', lineWidth: 2 },
      { position: 1666216800, text: '10-20', lineWidth: 2 },
      { position: 1666476000, text: '10-23', lineWidth: 2 },
      { position: 1666735200, text: '10-26', lineWidth: 2 },
      { position: 1666994400, text: '10-29', lineWidth: 2 },
      { position: 1667257200, text: '11-01', lineWidth: 2 },
      { position: 1667516400, text: '11-04', lineWidth: 2 },
      { position: 1667775600, text: '11-07', lineWidth: 2 },
      { position: 1668034800, text: '11-10', lineWidth: 2 },
      { position: 1668294000, text: '11-13', lineWidth: 2 }
    ])
  })

  test('labels a multi-year (400d) range as YYYY-MM-DD', () => {
    const ticks = computeTimeAxis(1633910400, 1668470400, 70, 86400, BERLIN)
    expect(ticks).toEqual([
      { position: 1638313200, text: '2021-12-01', lineWidth: 2 },
      { position: 1643670000, text: '2022-02-01', lineWidth: 2 },
      { position: 1648764000, text: '2022-04-01', lineWidth: 2 },
      { position: 1654034400, text: '2022-06-01', lineWidth: 2 },
      { position: 1659304800, text: '2022-08-01', lineWidth: 2 },
      { position: 1664575200, text: '2022-10-01', lineWidth: 2 }
    ])
  })
})

describe('computeTimeAxis calendar alignment', () => {
  test('aligns weekly-spaced ticks to Mondays', () => {
    const start = 1659312000
    const end = start + 60 * 86400
    const ticks = computeTimeAxis(start, end, 70, 3600, BERLIN)
    expect(ticks.length).toBeGreaterThan(2)
    for (const tick of ticks) {
      expect(getDayOfWeek(fromAbsolute(tick.position * 1000, BERLIN), 'en-GB')).toBe(0)
    }
  })
})

describe('computeTimeAxis timezone handling', () => {
  test('produces different tick instants in UTC than in Europe/Berlin', () => {
    const start = 1665486000
    const end = 1668519000
    const berlin = computeTimeAxis(start, end, 70, 9000, BERLIN)
    const utc = computeTimeAxis(start, end, 70, 9000, 'UTC')
    expect(utc.map((tick) => tick.position)).not.toEqual(berlin.map((tick) => tick.position))
  })

  test('aligns ticks to local midnight in a half-hour-offset zone (Asia/Kolkata)', () => {
    const ticks = computeTimeAxis(1665486000, 1668519000, 70, 9000, 'Asia/Kolkata')
    const gridTicks = ticks.filter((tick) => tick.lineWidth > 0)
    expect(gridTicks.length).toBeGreaterThan(0)
    for (const tick of gridTicks) {
      const zoned = fromAbsolute(tick.position * 1000, 'Asia/Kolkata')
      expect(zoned.hour).toBe(0)
      expect(zoned.minute).toBe(0)
    }
  })

  test('keeps daily ticks on local midnight across a DST spring-forward (Europe/Berlin)', () => {
    const start = Date.UTC(2024, 2, 25) / 1000
    const end = Date.UTC(2024, 3, 6) / 1000
    const ticks = computeTimeAxis(start, end, 70, 3600, BERLIN)
    const gridTicks = ticks.filter((tick) => tick.lineWidth > 0)
    expect(gridTicks.length).toBeGreaterThan(2)
    for (const tick of gridTicks) {
      expect(fromAbsolute(tick.position * 1000, BERLIN).hour).toBe(0)
    }
  })
})

describe('computeTimeAxis guards', () => {
  test('returns no ticks for an empty range (end <= start after trimming)', () => {
    const start = 1_700_000_000
    const step = 60
    const end = start + 2 * step
    expect(computeTimeAxis(start, end, 70, step, BERLIN)).toEqual([])
  })

  test('yields at least two ticks on a very narrow plot', () => {
    const ticks = computeTimeAxis(1668502320, 1668516720, 4, 60, BERLIN)
    expect(ticks.length).toBeGreaterThanOrEqual(2)
  })

  test('anchors sub-day ticks to the local-midnight grid', () => {
    const ticks = computeTimeAxis(1668502320, 1668516720, 70, 60, BERLIN)
    const spacing = ticks[1]!.position - ticks[0]!.position
    for (const tick of ticks) {
      const zoned = fromAbsolute(tick.position * 1000, BERLIN)
      const secondsSinceMidnight = zoned.hour * 3600 + zoned.minute * 60 + zoned.second
      expect(secondsSinceMidnight % spacing).toBe(0)
    }
  })
})
