/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test, vi } from 'vitest'

import {
  crosshairCentreX,
  drawCrosshair,
  drawPinLine,
  pinLineCentreX
} from '@/graphing/components/TimeSeriesGraph/overlay/crosshair'

function makeSpyCtx() {
  return {
    beginPath: vi.fn(),
    closePath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    setLineDash: vi.fn(),
    strokeStyle: '',
    fillStyle: '',
    lineWidth: 0
  }
}

describe('crosshairCentreX', () => {
  test('snaps a fractional x to the centre of the pixel column the hairline fills', () => {
    expect(crosshairCentreX(148.2)).toBe(148.5)
    expect(crosshairCentreX(147.8)).toBe(148.5)
  })

  test('an integer x is moved to that column, not left on the boundary', () => {
    expect(crosshairCentreX(148)).toBe(148.5)
  })
})

describe('pinLineCentreX', () => {
  test('snaps a fractional x to the centre of the pixel column the pin line fills', () => {
    expect(pinLineCentreX(382.33)).toBe(382.5)
    expect(pinLineCentreX(381.6)).toBe(382.5)
  })
})

describe('drawCrosshair', () => {
  test('draws the hairline at the x that crosshairCentreX reports', () => {
    const ctx = makeSpyCtx()

    drawCrosshair(ctx as unknown as CanvasRenderingContext2D, 148.2, 100)

    expect(ctx.moveTo).toHaveBeenCalledWith(crosshairCentreX(148.2), 0)
    expect(ctx.lineTo).toHaveBeenCalledWith(crosshairCentreX(148.2), 100)
  })
})

describe('drawPinLine', () => {
  test('draws a hairline at the x that pinLineCentreX reports', () => {
    const ctx = makeSpyCtx()

    drawPinLine(ctx as unknown as CanvasRenderingContext2D, 382.33, 100, '#15d1a0')

    expect(ctx.moveTo).toHaveBeenCalledWith(pinLineCentreX(382.33), 0)
    expect(ctx.lineTo).toHaveBeenCalledWith(pinLineCentreX(382.33), 100)
    expect(ctx.lineWidth).toBe(1)
  })

  test('strokes in the colour it is given, so the line matches the pin marker', () => {
    const ctx = makeSpyCtx()

    drawPinLine(ctx as unknown as CanvasRenderingContext2D, 382.33, 100, '#0f9472')

    expect(ctx.strokeStyle).toBe('#0f9472')
  })

  test('never inherits the crosshair dashes', () => {
    const ctx = makeSpyCtx()

    drawPinLine(ctx as unknown as CanvasRenderingContext2D, 382.33, 100, '#15d1a0')

    expect(ctx.setLineDash).toHaveBeenCalledWith([])
  })
})
