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
    checkmkUrl: () => 'https://cmk.example.com/mysite'
  })
}

describe('serviceChips', () => {
  // The same states in the same order as the hover card, so the two read alike.
  it('lists every service state in view order, zeros included', () => {
    const { serviceChips } = setup(
      obj('host', { host_name: 'web01' }),
      state({ services_summary: summary({ critical: 2, warning: 1, ok: 3 }) })
    )
    expect(serviceChips.value.map((c) => [c.label, c.count])).toEqual([
      ['OK', 3],
      ['WARN', 1],
      ['CRIT', 2],
      ['UNKNOWN', 0],
      ['PENDING', 0]
    ])
  })

  // A host whose services were never checked would otherwise read "0 OK".
  it('counts services that were never checked', () => {
    const { serviceChips } = setup(
      obj('host', { host_name: 'web01' }),
      state({ services_summary: summary({ pending: 4 }) })
    )
    expect(serviceChips.value.find((c) => c.label === 'PENDING')?.count).toBe(4)
  })

  it('is empty without a services_summary', () => {
    const { serviceChips } = setup(obj('host'), state())
    expect(serviceChips.value).toEqual([])
  })

  it('links service chips to the checkmk view for a host', () => {
    const { serviceChips } = setup(
      obj('host', { host_name: 'web01' }),
      state({ services_summary: summary({ critical: 1 }) })
    )
    const crit = serviceChips.value.find((c) => c.label === 'CRIT')
    expect(crit!.url).toContain('web01')
  })
})

describe('hostChips / hostsSummary', () => {
  it('lists every host state of a site in view order, zeros included', () => {
    const { hostChips } = setup(
      obj('site', { host_name: 'mysite' }),
      state({ type: 'site', hosts_summary: summary({ ok: 10, pending: 2 }) })
    )
    expect(hostChips.value.map((c) => [c.label, c.count])).toEqual([
      ['UP', 10],
      ['DOWN', 0],
      ['UNREACH', 0],
      ['PENDING', 2]
    ])
  })

  it('links the host chips of a site to its hosts', () => {
    const { hostChips } = setup(
      obj('site', { host_name: 'mysite' }),
      state({ type: 'site', hosts_summary: summary({ ok: 1 }) })
    )
    expect(hostChips.value[0]!.url).toContain('site=mysite')
  })

  function hostgroupChips() {
    return setup(
      obj('hostgroup', { group_name: 'linux' }),
      state({
        hosts_summary: summary({ ok: 3, critical: 1 }),
        services_summary: summary({ ok: 9, warning: 2 })
      })
    )
  }

  it('shows a hostgroup its hosts', () => {
    const { hostChips } = hostgroupChips()
    const hosts = Object.fromEntries(hostChips.value.map((c) => [c.label, c.count]))
    expect(hosts).toEqual({ UP: 3, DOWN: 1, UNREACH: 0, PENDING: 0 })
  })

  it('shows a hostgroup the services of its hosts', () => {
    const { serviceChips } = hostgroupChips()
    const services = Object.fromEntries(serviceChips.value.map((c) => [c.label, c.count]))
    expect(services).toEqual({ OK: 9, WARN: 2, CRIT: 0, UNKNOWN: 0, PENDING: 0 })
  })

  it('links the service chips of a hostgroup to its services', () => {
    const { serviceChips } = hostgroupChips()
    expect(decodeURIComponent(serviceChips.value[0]!.url ?? '')).toContain('opthost_group=linux')
  })

  it('uses hosts_summary directly when present', () => {
    const { hostChips } = setup(
      obj('dyngroup', { object_filter: 'x' }),
      state({ hosts_summary: summary({ ok: 7, critical: 2 }) })
    )
    const byState = Object.fromEntries(hostChips.value.map((c) => [c.label, c.count]))
    expect(byState.UP).toBe(7)
    expect(byState.DOWN).toBe(2)
  })

  it('returns no host chips for a plain host', () => {
    const { hostChips } = setup(obj('host', { host_name: 'web01' }), state())
    expect(hostChips.value).toEqual([])
  })
})
