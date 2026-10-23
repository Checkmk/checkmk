/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  dockTargetAt,
  elementBounds,
  isDocked,
  undockFrom
} from '@/maps/map/presentation/connectors'
import { createElement } from '@/maps/map/presentation/elements'
import type { DataElement, PresentationElement, ShapeElement } from '@/maps/types/api'

function data(over: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', 0, 0)
  if (el.kind !== 'data') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

function line(x = 0, y = 0): ShapeElement {
  const el = createElement('line', x, y)
  if (el.kind !== 'shape') {
    throw new Error('unreachable')
  }
  return el
}

function lookup(els: PresentationElement[]) {
  return (id: string | null | undefined) => els.find((el) => el.id === id)
}

describe('elementBounds', () => {
  it('returns the element box for non-connectors', () => {
    const el = data({ x: 10, y: 20, w: 100, h: 50 })
    expect(elementBounds(el, () => undefined)).toEqual({ x: 10, y: 20, w: 100, h: 50 })
  })

  it('spans a docked connector between its endpoint centres', () => {
    const a = data({ x: 0, y: 0, w: 100, h: 100 })
    const b = data({ x: 400, y: 200, w: 100, h: 100 })
    const link = line()
    link.start_ref = a.id
    link.end_ref = b.id
    const byId = lookup([a, b])
    // Endpoint centres: (50,50) and (450,250).
    expect(elementBounds(link, byId)).toEqual({ x: 50, y: 50, w: 400, h: 200 })
  })

  it('falls back to the connector corners for free endpoints', () => {
    const link = line(30, 40)
    link.w = 260
    link.h = 4
    expect(elementBounds(link, () => undefined)).toEqual({ x: 30, y: 40, w: 260, h: 4 })
  })
})

describe('undockFrom', () => {
  it('leaves the freed end where the removed element was', () => {
    const a = data({ x: 0, y: 0, w: 100, h: 100 })
    const b = data({ x: 400, y: 200, w: 100, h: 100 })
    const link = line()
    link.start_ref = a.id
    link.end_ref = b.id

    undockFrom([link, a], new Set([b.id]), lookup([a, b, link]))

    expect(link.end_ref).toBeNull()
    expect(link.start_ref).toBe(a.id)
    // The box now spans the centres the connector had while docked.
    expect(elementBounds(link, lookup([a, link]))).toEqual({ x: 50, y: 50, w: 400, h: 200 })
  })

  it('does not touch a connector that referenced nothing removed', () => {
    const a = data({ x: 0, y: 0, w: 100, h: 100 })
    const other = data({ x: 700, y: 700, w: 10, h: 10 })
    const link = line(30, 40)
    link.start_ref = a.id

    undockFrom([link], new Set([other.id]), lookup([a, other, link]))

    expect(link.start_ref).toBe(a.id)
    expect({ x: link.x, y: link.y }).toEqual({ x: 30, y: 40 })
  })
})

describe('isDocked', () => {
  it('is true as soon as one end references an element', () => {
    const target = data({ x: 0, y: 0, w: 10, h: 10 })
    const free = line()
    const docked = line()
    docked.end_ref = target.id
    const byId = lookup([target, free, docked])
    expect(isDocked(free, byId)).toBe(false)
    expect(isDocked(docked, byId)).toBe(true)
  })
})

describe('dockTargetAt', () => {
  const never = () => false

  it('picks the topmost element under the point', () => {
    const low = data({ x: 0, y: 0, w: 100, h: 100, z: 1 })
    const high = data({ x: 50, y: 50, w: 100, h: 100, z: 2 })
    expect(dockTargetAt([low, high], { x: 60, y: 60 }, 'other', never)).toBe(high.id)
  })

  it('never docks to the connector itself, to another connector, or to a group member', () => {
    const self = line()
    const other = line(10, 10)
    other.w = 100
    other.h = 100
    const member = data({ x: 0, y: 0, w: 100, h: 100 })
    const inGroup = (id: string) => id === member.id
    expect(dockTargetAt([self, other, member], { x: 20, y: 20 }, self.id, inGroup)).toBeNull()
  })

  it('reports nothing where the point misses every element', () => {
    const el = data({ x: 0, y: 0, w: 10, h: 10 })
    expect(dockTargetAt([el], { x: 500, y: 500 }, 'other', never)).toBeNull()
  })
})
