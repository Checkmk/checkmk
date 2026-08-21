/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const COLOR_WHITE_10 = 'rgb(255 255 255 / 10%)'
const CROSSHAIR_GREY = '#8a8a8a'

const FOCUS_DOT_RADIUS = 4
const FOCUS_HALO_RADIUS = 8
const FOCUS_HALO_STROKE_WIDTH = 8

export function crosshairCentreX(snapX: number): number {
  return Math.round(snapX) + 0.5
}

export function pinLineCentreX(pinX: number): number {
  return Math.round(pinX) + 0.5
}

export function drawCrosshair(ctx: CanvasRenderingContext2D, snapX: number, height: number): void {
  const pixelAlignedX = crosshairCentreX(snapX)
  ctx.beginPath()
  ctx.setLineDash([3, 3])
  ctx.strokeStyle = CROSSHAIR_GREY
  ctx.lineWidth = 1
  ctx.moveTo(pixelAlignedX, 0)
  ctx.lineTo(pixelAlignedX, height)
  ctx.stroke()
  ctx.setLineDash([])
}

export function drawPinLine(
  ctx: CanvasRenderingContext2D,
  x: number,
  height: number,
  color: string
): void {
  const pixelAlignedX = pinLineCentreX(x)
  ctx.beginPath()
  ctx.setLineDash([])
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.moveTo(pixelAlignedX, 0)
  ctx.lineTo(pixelAlignedX, height)
  ctx.stroke()
}

export interface FocusDot {
  x: number
  y: number
  color: string
  closest: boolean
}

export function drawFocusDots(
  ctx: CanvasRenderingContext2D,
  dots: FocusDot[],
  strokeColor: string
): void {
  ctx.setLineDash([])
  for (const dot of dots) {
    if (dot.closest) {
      drawClosestHalo(ctx, dot)
    }
  }
  for (const dot of dots) {
    drawDot(ctx, dot, strokeColor)
  }
}

function drawClosestHalo(ctx: CanvasRenderingContext2D, dot: FocusDot): void {
  ctx.beginPath()
  ctx.arc(dot.x, dot.y, FOCUS_HALO_RADIUS, 0, Math.PI * 2)
  ctx.lineWidth = FOCUS_HALO_STROKE_WIDTH
  ctx.strokeStyle = COLOR_WHITE_10
  ctx.stroke()
}

function drawDot(ctx: CanvasRenderingContext2D, dot: FocusDot, strokeColor: string): void {
  ctx.beginPath()
  ctx.arc(dot.x, dot.y, FOCUS_DOT_RADIUS, 0, Math.PI * 2)
  ctx.fillStyle = dot.color
  ctx.fill()
  ctx.lineWidth = 1
  ctx.strokeStyle = strokeColor
  ctx.stroke()
}
