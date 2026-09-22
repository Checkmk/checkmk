/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  applyBindingDrop,
  bindableElementAt,
  parseBindingDropPayload
} from '@/maps/map/presentation/bindingDrop'
import { createElement } from '@/maps/map/presentation/elements'
import type { DataElement, PresentationElement, ShapeElement } from '@/maps/types/api'

function data(x: number, y: number, over: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', x, y)
  if (el.kind !== 'data') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

function rect(x: number, y: number, over: Partial<ShapeElement> = {}): ShapeElement {
  const el = createElement('rect', x, y)
  if (el.kind !== 'shape') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

describe('parseBindingDropPayload', () => {
  it('accepts every binding kind', () => {
    expect(parseBindingDropPayload('{"kind":"host","name":"web01","service":"CPU"}')).toEqual({
      kind: 'host',
      name: 'web01',
      service: 'CPU'
    })
    expect(parseBindingDropPayload('{"kind":"hostgroup","name":"linux"}')).toEqual({
      kind: 'hostgroup',
      name: 'linux',
      service: null
    })
    expect(parseBindingDropPayload('{"kind":"aggregation","name":"aggr1"}')).toEqual({
      kind: 'aggregation',
      name: 'aggr1',
      service: null
    })
  })

  it('keeps accepting the legacy host payload shape', () => {
    expect(parseBindingDropPayload('{"host":"web01","service":"CPU"}')).toEqual({
      kind: 'host',
      name: 'web01',
      service: 'CPU'
    })
  })

  it('rejects garbage', () => {
    expect(parseBindingDropPayload('not json')).toBeNull()
    expect(parseBindingDropPayload('{"service":"CPU"}')).toBeNull()
    expect(parseBindingDropPayload('null')).toBeNull()
  })
})

describe('bindableElementAt', () => {
  it('hits the topmost bindable element by z-order', () => {
    const low = data(0, 0, { z: 1 })
    const high = data(50, 50, { z: 5 })
    const els: PresentationElement[] = [low, high]
    expect(bindableElementAt(els, { x: 80, y: 80 })?.id).toBe(high.id)
  })

  it('ignores connectors, locked, hidden and non-bindable elements', () => {
    const line = createElement('line', 0, 0)
    const locked = data(0, 0, { locked: true })
    const hidden = data(0, 0, { hidden: true })
    const text = createElement('text', 0, 0)
    expect(bindableElementAt([line, locked, hidden, text], { x: 10, y: 10 })).toBeNull()
  })
})

describe('applyBindingDrop', () => {
  it('binds the hit element and clears stale fields from other binding types', () => {
    const target = rect(0, 0, {
      object_type: 'hostgroup',
      group_name: 'linux'
    })
    const result = applyBindingDrop([target], { x: 10, y: 10 }, { kind: 'host', name: 'web01' }, 7)
    expect(result.kind).toBe('bind')
    if (result.kind !== 'bind') {
      return
    }
    expect(result.id).toBe(target.id)
    expect(result.patch).toEqual({
      object_type: null,
      host_name: 'web01',
      service_description: null,
      group_name: null,
      aggregation_id: null
    })
  })

  it('binds groups and aggregations with their explicit object type', () => {
    const target = data(0, 0, { host_name: 'old', service_description: 'CPU' })
    const group = applyBindingDrop(
      [target],
      { x: 10, y: 10 },
      { kind: 'servicegroup', name: 'https' },
      7
    )
    if (group.kind !== 'bind') {
      throw new Error('expected bind')
    }
    expect(group.patch).toMatchObject({
      object_type: 'servicegroup',
      group_name: 'https',
      host_name: null,
      service_description: null
    })

    const bi = applyBindingDrop([target], { x: 10, y: 10 }, { kind: 'aggregation', name: 'a1' }, 7)
    if (bi.kind !== 'bind') {
      throw new Error('expected bind')
    }
    expect(bi.patch).toMatchObject({ object_type: 'aggregation', aggregation_id: 'a1' })
  })

  it('creates a bound data element on empty slide space', () => {
    const result = applyBindingDrop(
      [],
      { x: 500, y: 400 },
      { kind: 'host', name: 'web01', service: 'CPU' },
      7
    )
    expect(result.kind).toBe('create')
    if (result.kind !== 'create') {
      return
    }
    expect(result.element.kind).toBe('data')
    expect(result.element.host_name).toBe('web01')
    expect(result.element.service_description).toBe('CPU')
    expect(result.element.z).toBe(7)
    expect(result.element.x).toBe(420)
    expect(result.element.y).toBe(340)
  })

  it('creates an aggregation-bound element on empty space', () => {
    const result = applyBindingDrop(
      [],
      { x: 500, y: 400 },
      { kind: 'aggregation', name: 'aggr1' },
      3
    )
    if (result.kind !== 'create') {
      throw new Error('expected create')
    }
    expect(result.element.object_type).toBe('aggregation')
    expect(result.element.aggregation_id).toBe('aggr1')
    expect(result.element.host_name).toBeNull()
  })
})
