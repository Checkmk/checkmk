/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export type BrushMode = 'move' | 'resize-l' | 'resize-r' | 'recenter'

export function timeToPx(
  time: number,
  domainStart: number,
  domainEnd: number,
  trackLeft: number,
  trackWidth: number
): number {
  return trackLeft + ((time - domainStart) / (domainEnd - domainStart)) * trackWidth
}

export function pxToTime(
  px: number,
  domainStart: number,
  domainEnd: number,
  trackLeft: number,
  trackWidth: number
): number {
  return domainStart + ((px - trackLeft) / trackWidth) * (domainEnd - domainStart)
}

export interface ResizeHandleRects {
  leftX: number
  rightX: number
  width: number
}

export function resizeHandleRects(
  windowLeftPx: number,
  windowRightPx: number,
  handleWidth: number
): ResizeHandleRects {
  return {
    leftX: windowLeftPx - handleWidth,
    rightX: windowRightPx,
    width: handleWidth
  }
}

export function hitTestMode(
  px: number,
  windowLeftPx: number,
  windowRightPx: number,
  resizeHandles: ResizeHandleRects
): BrushMode {
  if (px >= resizeHandles.leftX && px <= resizeHandles.leftX + resizeHandles.width) {
    return 'resize-l'
  }
  if (px >= resizeHandles.rightX && px <= resizeHandles.rightX + resizeHandles.width) {
    return 'resize-r'
  }
  if (px > windowLeftPx && px < windowRightPx) {
    return 'move'
  }
  return 'recenter'
}

export function clampMove(
  from: number,
  to: number,
  domainStart: number,
  domainEnd: number
): [number, number] {
  const span = to - from
  if (from < domainStart) {
    return [domainStart, domainStart + span]
  }
  if (to > domainEnd) {
    return [domainEnd - span, domainEnd]
  }
  return [from, to]
}

export function resizeLeft(
  newStart: number,
  windowEnd: number,
  domainStart: number,
  minSpan: number
): number {
  return Math.max(domainStart, Math.min(newStart, windowEnd - minSpan))
}

export function resizeRight(
  newEnd: number,
  windowStart: number,
  domainEnd: number,
  minSpan: number
): number {
  return Math.min(domainEnd, Math.max(newEnd, windowStart + minSpan))
}

export function recenter(
  center: number,
  span: number,
  domainStart: number,
  domainEnd: number
): [number, number] {
  return clampMove(center - span / 2, center + span / 2, domainStart, domainEnd)
}
