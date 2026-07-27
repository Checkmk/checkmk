/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  clampPixelToPlot,
  clampSpan,
  selectionRect
} from '@/graphing/components/TimeSeriesGraph/interaction/selection'

describe('clampPixelToPlot', () => {
  const plotExtent = 200

  test('holds a pixel past the far edge at the plot extent', () => {
    const pixelPastTheFarEdge = 900

    const clamped = clampPixelToPlot(pixelPastTheFarEdge, plotExtent)

    expect(clamped).toBe(200)
  })

  test('holds a pixel before the near edge at zero', () => {
    const pixelBeforeTheNearEdge = -500

    const clamped = clampPixelToPlot(pixelBeforeTheNearEdge, plotExtent)

    expect(clamped).toBe(0)
  })

  test('leaves a pixel inside the plot untouched', () => {
    const pixelInsideThePlot = 120

    const clamped = clampPixelToPlot(pixelInsideThePlot, plotExtent)

    expect(clamped).toBe(120)
  })
})

describe('clampSpan', () => {
  test('widens a sub-floor range about its centre', () => {
    const range: [number, number] = [100, 110]
    const floor = 100

    const widened = clampSpan(range, floor)

    expect(widened).toEqual([55, 155])
  })

  test('leaves a wide-enough range untouched', () => {
    const range: [number, number] = [0, 200]
    const floor = 100

    const result = clampSpan(range, floor)

    expect(result).toEqual([0, 200])
  })

  test('is a no-op when the floor is null', () => {
    const range: [number, number] = [100, 110]

    const result = clampSpan(range, null)

    expect(result).toEqual([100, 110])
  })
})

describe('selectionRect', () => {
  const plot = { left: 50, top: 10, width: 200, height: 100 }

  test('time mode spans the x drag across the full plot height', () => {
    const points = { x0: 80, y0: 40, x1: 180, y1: 90 }

    const rect = selectionRect('time', points, plot)

    expect(rect).toEqual({ x: 80, y: 10, width: 100, height: 100 })
  })

  test('value mode spans the y drag across the full plot width', () => {
    const points = { x0: 80, y0: 90, x1: 180, y1: 40 }

    const rect = selectionRect('value', points, plot)

    expect(rect).toEqual({ x: 50, y: 40, width: 200, height: 50 })
  })

  test('clamps drag points that fall outside the plot box', () => {
    const points = { x0: 20, y0: 40, x1: 300, y1: 90 }

    const rect = selectionRect('time', points, plot)

    expect(rect).toEqual({ x: 50, y: 10, width: 200, height: 100 })
  })
})
