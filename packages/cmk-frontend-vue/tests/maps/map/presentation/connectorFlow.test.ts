/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { flowVisual } from '@/maps/map/presentation/connectorFlow'
import { createElement } from '@/maps/map/presentation/elements'
import type { ObjectState, ShapeElement } from '@/maps/types/api'

import { aState } from '../../support/fixtures'

function link(over: Partial<ShapeElement> = {}): ShapeElement {
  const el = createElement('line', 0, 0)
  if (el.kind !== 'shape') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

function state(perf: string): ObjectState {
  return aState({
    object_id: 'x',
    type: 'service',
    state: 'OK',
    output: '',
    perf_data: perf,
    acknowledged: false,
    in_downtime: false,
    stale: false
  })
}

describe('flowVisual', () => {
  it('resolves each direction with its own metric via the override', () => {
    const el = link({
      host_name: 'sw1',
      flow: true,
      flow_metric: 'in',
      flow_metric_back: 'out'
    })
    const s = state('in=20%;80;90;0;100 out=90%;80;90;0;100')
    const forward = flowVisual(el, s)
    const back = flowVisual(el, s, el.flow_metric_back ?? null)
    expect(forward.util).toBe(20)
    expect(back.util).toBe(90)
    expect(back.width).toBeGreaterThan(forward.width)
    expect(back.durationSec!).toBeLessThan(forward.durationSec!)
  })

  it('colours group-bound connectors by state (not only host bindings)', () => {
    const el = link({ object_type: 'hostgroup', group_name: 'linux' })
    const vis = flowVisual(el, { ...state(''), state: 'CRITICAL' })
    expect(vis.color).not.toBe('var(--pres-shape-stroke)')
    expect(vis.valueText).toBe('CRITICAL')
  })

  it('keeps the static dash style when not flowing', () => {
    const el = link({ dash: 'dotted', stroke_width: 4 })
    const vis = flowVisual(el, undefined)
    expect(vis.durationSec).toBeNull()
    expect(vis.dashArray).toBe('4 6')
  })
})
