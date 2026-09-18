/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  clampMove,
  hitTestMode,
  pxToTime,
  recenter,
  resizeHandleRects,
  resizeLeft,
  resizeRight,
  timeToPx
} from '@/graphing/components/GraphBrush/geometry'

const domain = { start: 0, end: 1000 }
const track = { left: 0, width: 100 } // 10s per px
const handleWidth = 8

describe('timeToPx', () => {
  test('maps a domain value linearly onto the track', () => {
    const midDomain = 500

    const px = timeToPx(midDomain, domain.start, domain.end, track.left, track.width)

    expect(px).toBe(50)
  })
})

describe('pxToTime', () => {
  test('maps a track pixel back onto the domain (inverse of timeToPx)', () => {
    const midTrack = 50

    const time = pxToTime(midTrack, domain.start, domain.end, track.left, track.width)

    expect(time).toBe(500)
  })

  test('round-trips with timeToPx', () => {
    const originalTime = 250

    const px = timeToPx(originalTime, domain.start, domain.end, track.left, track.width)
    const time = pxToTime(px, domain.start, domain.end, track.left, track.width)

    expect(time).toBe(originalTime)
  })
})

describe('hitTestMode', () => {
  const windowLeftPx = 40
  const windowRightPx = 60
  const resizeHandles = resizeHandleRects(windowLeftPx, windowRightPx, handleWidth)

  test('a point on the left handle resizes from the left', () => {
    const onLeftHandle = resizeHandles.leftX + resizeHandles.width / 2

    const mode = hitTestMode(onLeftHandle, windowLeftPx, windowRightPx, resizeHandles)

    expect(mode).toBe('resize-l')
  })

  test('a point on the right handle resizes from the right', () => {
    const onRightHandle = resizeHandles.rightX + resizeHandles.width / 2

    const mode = hitTestMode(onRightHandle, windowLeftPx, windowRightPx, resizeHandles)

    expect(mode).toBe('resize-r')
  })

  test('a point inside the window moves it', () => {
    const insideWindow = (windowLeftPx + windowRightPx) / 2

    const mode = hitTestMode(insideWindow, windowLeftPx, windowRightPx, resizeHandles)

    expect(mode).toBe('move')
  })

  test('a point clear of the window and its handles recenters it', () => {
    const beforeLeftHandle = resizeHandles.leftX - 1

    const mode = hitTestMode(beforeLeftHandle, windowLeftPx, windowRightPx, resizeHandles)

    expect(mode).toBe('recenter')
  })
})

describe('clampMove', () => {
  test('shifts a window overrunning the left edge back in, preserving span', () => {
    const from = -100
    const to = 100

    const clamped = clampMove(from, to, domain.start, domain.end)

    expect(clamped).toEqual([0, 200])
  })

  test('shifts a window overrunning the right edge back in, preserving span', () => {
    const from = 900
    const to = 1100

    const clamped = clampMove(from, to, domain.start, domain.end)

    expect(clamped).toEqual([800, 1000])
  })
})

describe('resizeLeft / resizeRight (min-span bound)', () => {
  const minSpan = 100

  test('resizeLeft cannot cross windowEnd minus the min span', () => {
    const newStart = 950
    const windowEnd = 900

    const start = resizeLeft(newStart, windowEnd, domain.start, minSpan)

    expect(start).toBe(800)
  })

  test('resizeLeft clamps to the domain start', () => {
    const newStart = -50
    const windowEnd = 900

    const start = resizeLeft(newStart, windowEnd, domain.start, minSpan)

    expect(start).toBe(0)
  })

  test('resizeRight cannot cross windowStart plus the min span', () => {
    const newEnd = 120
    const windowStart = 100

    const end = resizeRight(newEnd, windowStart, domain.end, minSpan)

    expect(end).toBe(200)
  })
})

describe('recenter (span-preserving, clamped)', () => {
  const span = 200

  test('centers the window on the click', () => {
    const center = 500

    const windowRange = recenter(center, span, domain.start, domain.end)

    expect(windowRange).toEqual([400, 600])
  })

  test('clamps the window at the right edge', () => {
    const center = 990

    const windowRange = recenter(center, span, domain.start, domain.end)

    expect(windowRange).toEqual([800, 1000])
  })
})
