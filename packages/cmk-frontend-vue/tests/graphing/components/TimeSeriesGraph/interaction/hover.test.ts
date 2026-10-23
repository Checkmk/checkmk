/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { metricHitDistance } from '@/graphing/components/TimeSeriesGraph/interaction/hover'

const BAND_TOP = 40
const BAND_BOTTOM = 80

describe('metricHitDistance', () => {
  test('a line has no height, so the distance is the gap to its single edge from either side', () => {
    const edge = 80
    const gap = 20

    const fromBelow = metricHitDistance(edge + gap, edge, edge)
    const fromAbove = metricHitDistance(edge - gap, edge, edge)

    expect(fromBelow).toBe(gap)
    expect(fromAbove).toBe(gap)
  })

  test('a cursor inside a filled band, its edges included, is at zero distance', () => {
    const inside = [BAND_TOP, (BAND_TOP + BAND_BOTTOM) / 2, BAND_BOTTOM]

    const distances = inside.map((cursorY) => metricHitDistance(cursorY, BAND_TOP, BAND_BOTTOM))

    expect(distances).toEqual([0, 0, 0])
  })

  test('a cursor outside a filled band measures to the nearer edge', () => {
    const gap = 10

    const above = metricHitDistance(BAND_TOP - gap, BAND_TOP, BAND_BOTTOM)
    const below = metricHitDistance(BAND_BOTTOM + gap, BAND_TOP, BAND_BOTTOM)

    expect(above).toBe(gap)
    expect(below).toBe(gap)
  })

  test('the edges may arrive in either order, as a metric mirrored below zero hands them over', () => {
    const cursorY = BAND_BOTTOM + 15

    const upright = metricHitDistance(cursorY, BAND_TOP, BAND_BOTTOM)
    const mirrored = metricHitDistance(cursorY, BAND_BOTTOM, BAND_TOP)

    expect(mirrored).toBe(upright)
  })
})
