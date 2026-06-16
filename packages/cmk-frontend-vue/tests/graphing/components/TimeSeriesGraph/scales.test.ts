/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { buildXScale, buildYScale } from '@/graphing/components/TimeSeriesGraph/scales'

describe('buildXScale', () => {
  test('maps the time-range bounds onto [0, plotWidth]', () => {
    const timeRange = { start: 1000, end: 2000, step: 60 }
    const plotWidth = 800

    const xScale = buildXScale(timeRange, plotWidth)

    expect(xScale(new Date(1000 * 1000))).toBe(0)
    expect(xScale(new Date(2000 * 1000))).toBe(plotWidth)
  })

  test('places an interior timestamp proportionally', () => {
    const timeRange = { start: 1000, end: 2000, step: 60 }

    const xScale = buildXScale(timeRange, 800)

    expect(xScale(new Date(1500 * 1000))).toBe(400)
  })
})

describe('buildYScale', () => {
  test('maps the domain min to the padded bottom and max to the padded top', () => {
    const plotHeight = 100
    const padding = 10

    const yScale = buildYScale([0, 10], plotHeight, padding)

    expect(yScale(0)).toBe(plotHeight - padding)
    expect(yScale(10)).toBe(padding)
  })

  test('places an interior value proportionally', () => {
    const yScale = buildYScale([0, 10], 100, 10)

    expect(yScale(5)).toBe(50)
  })
})
