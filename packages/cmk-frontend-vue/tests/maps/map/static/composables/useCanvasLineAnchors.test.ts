/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { edgePoint } from '@/maps/map/static/composables/useCanvasLineAnchors'

const BOX = { x: 100, y: 100, halfX: 20, halfY: 10 }

describe('edgePoint', () => {
  it('meets the side the rest of the line is on', () => {
    expect(edgePoint(BOX, 500, 100)).toEqual({ x: 120, y: 100 })
    expect(edgePoint(BOX, -500, 100)).toEqual({ x: 80, y: 100 })
    expect(edgePoint(BOX, 100, 500)).toEqual({ x: 100, y: 110 })
    expect(edgePoint(BOX, 100, -500)).toEqual({ x: 100, y: 90 })
  })

  it('leaves the box by whichever side the ray reaches first', () => {
    // A wide, flat box: a diagonal ray leaves through the top, not the side.
    const point = edgePoint(BOX, 200, 200)
    expect(point.y).toBe(110)
    expect(point.x).toBe(110)
  })

  it('stays at the centre for a line that aims nowhere', () => {
    expect(edgePoint(BOX, 100, 100)).toEqual({ x: 100, y: 100 })
  })
})
