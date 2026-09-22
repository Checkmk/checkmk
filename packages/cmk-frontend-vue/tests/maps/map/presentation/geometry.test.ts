/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { type TransformOrigin, resizedBox, rotationFor } from '@/maps/map/presentation/geometry'

const BOX: TransformOrigin = { x: 100, y: 100, w: 200, h: 100, rotation: 0 }

function round(box: { x: number; y: number; w: number; h: number }) {
  return {
    x: Math.round(box.x),
    y: Math.round(box.y),
    w: Math.round(box.w),
    h: Math.round(box.h)
  }
}

describe('resizedBox', () => {
  it('grows from the east handle and leaves the west edge where it was', () => {
    const box = resizedBox(BOX, 'e', { x: 40, y: 0 }, false)
    expect(round(box)).toEqual({ x: 100, y: 100, w: 240, h: 100 })
  })

  it('moves the west edge and keeps the east one fixed', () => {
    const box = resizedBox(BOX, 'w', { x: 40, y: 0 }, false)
    expect(round(box)).toEqual({ x: 140, y: 100, w: 160, h: 100 })
    expect(box.x + box.w).toBe(BOX.x + BOX.w)
  })

  it('drags both axes from a corner handle', () => {
    const box = resizedBox(BOX, 'se', { x: 40, y: 20 }, false)
    expect(round(box)).toEqual({ x: 100, y: 100, w: 240, h: 120 })
  })

  it('keeps the aspect ratio when asked', () => {
    const box = resizedBox(BOX, 'se', { x: 100, y: 0 }, true)
    expect(box.w / box.h).toBeCloseTo(BOX.w / BOX.h)
  })

  it('never shrinks a side below the minimum', () => {
    const box = resizedBox(BOX, 'e', { x: -1000, y: 0 }, false)
    expect(box.w).toBe(8)
  })

  it('holds the minimum with the ratio, which would otherwise re-derive under it', () => {
    // 20x200: clamping w to 8 and then applying the 1:10 ratio would put h at
    // 80 but w back at 8 -- the ratio has to lift both instead.
    const thin: TransformOrigin = { x: 0, y: 0, w: 20, h: 200, rotation: 0 }
    const box = resizedBox(thin, 'e', { x: -1000, y: 0 }, true)
    expect(box.w).toBeGreaterThanOrEqual(8)
    expect(box.h).toBeGreaterThanOrEqual(8)
    expect(box.w / box.h).toBeCloseTo(thin.w / thin.h)
  })

  it('resizes a rotated element along its own edges, keeping the fixed edge put', () => {
    const rotated: TransformOrigin = { ...BOX, rotation: 90 }
    // At 90° the element's own +x axis points down the slide, so dragging its
    // east handle downwards grows its width, and its centre travels half that
    // growth in the same direction.
    const box = resizedBox(rotated, 'e', { x: 0, y: 40 }, false)
    expect(round(box)).toEqual({ x: 80, y: 120, w: 240, h: 100 })
    // The grabbed edge moved, the opposite one did not: at 90° the fixed west
    // edge sits at the centre plus (-w/2, 0) rotated into slide space.
    const west = (b: typeof box) => ({ x: b.x + b.w / 2, y: b.y + b.h / 2 - b.w / 2 })
    expect(west(box)).toEqual(west(rotated))
  })
})

describe('rotationFor', () => {
  it('points the top edge at the pointer', () => {
    // Straight above the centre is 0°, to the right is 90°.
    expect(rotationFor(BOX, { x: 200, y: 0 }, false)).toBe(0)
    expect(rotationFor(BOX, { x: 500, y: 150 }, false)).toBe(90)
    expect(rotationFor(BOX, { x: 200, y: 500 }, false)).toBe(180)
  })

  it('snaps to 15° steps', () => {
    const free = rotationFor(BOX, { x: 260, y: 20 }, false)
    const snapped = rotationFor(BOX, { x: 260, y: 20 }, true)
    expect(snapped % 15).toBe(0)
    expect(Math.abs(snapped - free)).toBeLessThanOrEqual(8)
  })
})
