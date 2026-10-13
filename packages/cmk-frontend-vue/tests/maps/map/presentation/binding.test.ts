/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { isBindable, isBoundElement, isUnboundSlot } from '@/maps/map/presentation/binding'
import { createElement } from '@/maps/map/presentation/elements'
import type { DataElement, ShapeElement } from '@/maps/types/api'

function data(over: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', 0, 0)
  if (el.kind !== 'data') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

function shape(over: Partial<ShapeElement> = {}): ShapeElement {
  const el = createElement('rect', 0, 0)
  if (el.kind !== 'shape') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

describe('isUnboundSlot', () => {
  it('treats an unbound data element as a slot, a bound one not', () => {
    expect(isUnboundSlot(data())).toBe(true)
    expect(isUnboundSlot(data({ host_name: 'web01' }))).toBe(false)
  })

  it('treats a shape as a slot only when explicitly marked', () => {
    expect(isUnboundSlot(shape())).toBe(false)
    expect(isUnboundSlot(shape({ data_slot: true }))).toBe(true)
    expect(isUnboundSlot(shape({ data_slot: true, host_name: 'web01' }))).toBe(false)
  })

  it('never treats text/image/group as slots', () => {
    expect(isUnboundSlot(createElement('text', 0, 0))).toBe(false)
    expect(isUnboundSlot(createElement('image', 0, 0))).toBe(false)
  })
})

describe('isBindable / isBoundElement', () => {
  it('classifies element kinds', () => {
    expect(isBindable(data())).toBe(true)
    expect(isBindable(shape())).toBe(true)
    expect(isBindable(createElement('text', 0, 0))).toBe(false)
    expect(isBoundElement(data({ host_name: 'web01' }))).toBe(true)
    expect(isBoundElement(data())).toBe(false)
  })
})
