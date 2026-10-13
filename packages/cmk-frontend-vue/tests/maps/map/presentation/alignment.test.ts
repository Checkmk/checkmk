/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { alignedPosition, distributedPositions } from '@/maps/map/presentation/alignment'
import { createElement } from '@/maps/map/presentation/elements'
import type { PresentationElement } from '@/maps/types/api'

function box(x: number, y: number, w: number, h: number): PresentationElement {
  return Object.assign(createElement('rect', x, y), { w, h })
}

const SELECTION = { x: 0, y: 0, w: 400, h: 200 }

describe('alignedPosition', () => {
  const el = box(50, 50, 100, 40)

  it('lines an element up on each edge and centre of the selection', () => {
    expect(alignedPosition(el, SELECTION, 'left')).toEqual({ x: 0, y: 50 })
    expect(alignedPosition(el, SELECTION, 'center')).toEqual({ x: 150, y: 50 })
    expect(alignedPosition(el, SELECTION, 'right')).toEqual({ x: 300, y: 50 })
    expect(alignedPosition(el, SELECTION, 'top')).toEqual({ x: 50, y: 0 })
    expect(alignedPosition(el, SELECTION, 'middle')).toEqual({ x: 50, y: 80 })
    expect(alignedPosition(el, SELECTION, 'bottom')).toEqual({ x: 50, y: 160 })
  })
})

describe('distributedPositions', () => {
  it('evens out the gaps and leaves the outer two elements alone', () => {
    const a = box(0, 0, 100, 10)
    const b = box(120, 0, 100, 10)
    const c = box(400, 0, 100, 10)
    const positions = distributedPositions([b, c, a], 'x')
    expect(positions.get(a.id)).toBe(0)
    expect(positions.get(c.id)).toBe(400)
    // Two gaps of (500 - 300) / 2 = 100 each.
    expect(positions.get(b.id)).toBe(200)
  })

  it('works down the other axis too', () => {
    const a = box(0, 0, 10, 100)
    const b = box(0, 50, 10, 100)
    const c = box(0, 400, 10, 100)
    expect(distributedPositions([a, b, c], 'y').get(b.id)).toBe(200)
  })

  it('has nothing to do with fewer than three elements', () => {
    const a = box(0, 0, 10, 10)
    const b = box(100, 0, 10, 10)
    expect(distributedPositions([a, b], 'x').size).toBe(0)
    expect(distributedPositions([], 'x').size).toBe(0)
  })
})
