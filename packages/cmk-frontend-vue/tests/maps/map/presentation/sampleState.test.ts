/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { createElement } from '@/maps/map/presentation/elements'
import { sampleStateFor } from '@/maps/map/presentation/sampleState'
import type { DataElement } from '@/maps/types/api'

function data(over: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', 0, 0)
  if (el.kind !== 'data') {
    throw new Error('unreachable')
  }
  return Object.assign(el, over)
}

describe('sampleStateFor', () => {
  it('is deterministic per element id', () => {
    const el = data()
    const a = sampleStateFor(el)
    const b = sampleStateFor(el)
    expect(a).toEqual(b)
    expect(a.object_id).toBe(el.id)
  })

  it('carries a parsable perf_data metric matching the configured gadget metric', () => {
    const el = data({ display: { mode: 'gadget', gadget_type: 'gauge', gadget_metric: 'load1' } })
    const s = sampleStateFor(el)
    expect(s.perf_data.startsWith('load1=')).toBe(true)
    expect(s.perf_data).toMatch(/^load1=\d+%;80;90;0;100$/)
  })

  it('falls back to a generic util metric when none is configured', () => {
    expect(sampleStateFor(data()).perf_data).toMatch(/^util=\d+%/)
  })
})
