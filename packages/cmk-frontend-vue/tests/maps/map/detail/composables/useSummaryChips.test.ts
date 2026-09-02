/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useSummaryChips } from '@/maps/map/detail/composables/useSummaryChips'
import type { MapElement, ObjectState, ServicesSummary } from '@/maps/types/api'

import { aState, anObject } from '../../../support/fixtures'

function obj(type: MapElement['type'], extra: Partial<MapElement> = {}): MapElement {
  return anObject({ id: 'o', type, x: 0, y: 0, url_target: '', ...extra })
}

function summary(extra: Partial<ServicesSummary> = {}): ServicesSummary {
  return { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0, ...extra }
}

function state(extra: Partial<ObjectState> = {}): ObjectState {
  return aState({
    object_id: '',
    type: 'host',
    state: 'OK',
    output: '',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false,
    ...extra
  })
}

function setup(object: MapElement | null, st: ObjectState | undefined) {
  return useSummaryChips({
    object: () => object,
    state: () => st,
    checkmkUrl: () => 'https://cmk.example.com/mysite',
    isSite: () => object?.type === 'site'
  })
}

describe('serviceChips', () => {
  it('always keeps the OK anchor and hides zero problem chips', () => {
    const { serviceChips } = setup(
      obj('host', { host_name: 'web01' }),
      state({ services_summary: summary({ ok: 5 }) })
    )
    expect(serviceChips.value.map((c) => c.state)).toEqual(['OK'])
    expect(serviceChips.value[0]!.count).toBe(5)
  })

  it('includes problem chips with a non-zero count, worst first', () => {
    const { serviceChips } = setup(
      obj('host', { host_name: 'web01' }),
      state({ services_summary: summary({ critical: 2, warning: 1, ok: 3 }) })
    )
    expect(serviceChips.value.map((c) => c.state)).toEqual(['CRITICAL', 'WARNING', 'OK'])
  })

  it('is empty without a services_summary', () => {
    const { serviceChips } = setup(obj('host'), state())
    expect(serviceChips.value).toEqual([])
  })

  it('is empty for a hostgroup (its counts render as host chips)', () => {
    const { serviceChips } = setup(
      obj('hostgroup', { group_name: 'linux' }),
      state({ services_summary: summary({ ok: 4 }) })
    )
    expect(serviceChips.value).toEqual([])
  })

  it('links service chips to the checkmk view for a host', () => {
    const { serviceChips } = setup(
      obj('host', { host_name: 'web01' }),
      state({ services_summary: summary({ critical: 1 }) })
    )
    const crit = serviceChips.value.find((c) => c.state === 'CRITICAL')
    expect(crit!.url).toContain('web01')
  })
})

describe('hostChips / hostsSummary', () => {
  it('parses host counts from a site status output', () => {
    const { hostChips } = setup(
      obj('site', { host_name: 'mysite' }),
      state({ type: 'site', output: '504 hosts (502 up, 1 down, 1 unreachable)' })
    )
    const byState = Object.fromEntries(hostChips.value.map((c) => [c.state, c.count]))
    expect(byState).toEqual({ DOWN: 1, UNREACHABLE: 1, UP: 502 })
  })

  it('keeps the UP anchor and hides zero down/unreachable', () => {
    const { hostChips } = setup(
      obj('site', { host_name: 'mysite' }),
      state({ type: 'site', output: '10 hosts (10 up, 0 down, 0 unreachable)' })
    )
    expect(hostChips.value.map((c) => c.state)).toEqual(['UP'])
  })

  it('derives host chips from a hostgroup services_summary packing', () => {
    const { hostChips } = setup(
      obj('hostgroup', { group_name: 'linux' }),
      state({ services_summary: summary({ ok: 3, critical: 1 }) })
    )
    const byState = Object.fromEntries(hostChips.value.map((c) => [c.state, c.count]))
    expect(byState.UP).toBe(3)
    expect(byState.DOWN).toBe(1)
  })

  it('uses hosts_summary directly when present', () => {
    const { hostChips } = setup(
      obj('dyngroup', { object_filter: 'x' }),
      state({ hosts_summary: summary({ ok: 7, critical: 2 }) })
    )
    const byState = Object.fromEntries(hostChips.value.map((c) => [c.state, c.count]))
    expect(byState.UP).toBe(7)
    expect(byState.DOWN).toBe(2)
  })

  it('returns no host chips for a plain host', () => {
    const { hostChips } = setup(obj('host', { host_name: 'web01' }), state())
    expect(hostChips.value).toEqual([])
  })
})
