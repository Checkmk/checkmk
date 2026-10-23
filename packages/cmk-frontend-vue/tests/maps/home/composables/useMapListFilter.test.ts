/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'

import { useMapListFilter } from '@/maps/home/composables/useMapListFilter'
import type { MapRead } from '@/maps/types/api'

import { aListedMap } from '../../support/fixtures'
import { aTicket, fakeMapsServices, runWithServices } from '../../support/services'

function listed(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, ...over })
}

let services: ReturnType<typeof fakeMapsServices>

/** The list only knows the user once the session is there. */
async function setup(maps: MapRead[]) {
  services = fakeMapsServices({}, aTicket({ user_id: 'me' }))
  await services.auth.init(null)
  services.maps.maps.value = maps
  return runWithServices(services, () => useMapListFilter())
}

beforeEach(() => {
  services = fakeMapsServices()
})

describe('useMapListFilter — what is listed', () => {
  it('orders yours before others before built-in', async () => {
    const filter = await setup([
      listed('builtin', { is_builtin: true }),
      listed('theirs', { owner: 'someone' }),
      listed('mine', { owner: 'me' })
    ])
    expect(filter.displayedMaps.value.map((map) => map.name)).toEqual(['mine', 'theirs', 'builtin'])
  })

  it('lists a map hidden from the Monitor menu too', async () => {
    const filter = await setup([
      listed('shown'),
      listed('not-in-menu', { hide_in_monitor_menu: true })
    ])
    expect(filter.displayedMaps.value.map((map) => map.name)).toEqual(['shown', 'not-in-menu'])
  })

  it('searches name and display name', async () => {
    const filter = await setup([listed('prod-eu', { alias: 'Europe' }), listed('lab')])
    filter.searchQuery.value = 'europe'
    expect(filter.displayedMaps.value.map((map) => map.name)).toEqual(['prod-eu'])
    filter.searchQuery.value = 'LAB'
    expect(filter.displayedMaps.value.map((map) => map.name)).toEqual(['lab'])
  })
})

describe('useMapListFilter — scope', () => {
  it('offers the filter only once more than one kind of owner is present', async () => {
    const oneKind = await setup([listed('a', { owner: 'me' }), listed('b', { owner: 'me' })])
    expect(oneKind.showScopeFilter.value).toBe(false)
    const twoKinds = await setup([listed('a', { owner: 'me' }), listed('b', { is_builtin: true })])
    expect(twoKinds.showScopeFilter.value).toBe(true)
  })

  it('lists only the owner kinds that are actually there', async () => {
    const filter = await setup([listed('a', { owner: 'me' }), listed('b', { is_builtin: true })])
    expect(filter.scopeOptions.value.map((option) => option.value)).toEqual([
      'all',
      'you',
      'builtin'
    ])
  })

  it('narrows the list to the chosen kind', async () => {
    const filter = await setup([listed('a', { owner: 'me' }), listed('b', { is_builtin: true })])
    filter.scope.value = 'builtin'
    expect(filter.displayedMaps.value.map((map) => map.name)).toEqual(['b'])
  })

  it('falls back to all when the chosen kind is gone, rather than showing nothing', async () => {
    const filter = await setup([listed('a', { owner: 'me' }), listed('b', { is_builtin: true })])
    filter.scope.value = 'other'
    expect(filter.scope.value).toBe('all')
    expect(filter.displayedMaps.value).toHaveLength(2)
  })
})

describe('useMapListFilter — reordering', () => {
  it('allows a drag only while the shown order is the stored one', async () => {
    const filter = await setup([listed('a', { owner: 'me' }), listed('b', { owner: 'me' })])
    expect(filter.isOrderPristine.value).toBe(true)

    filter.searchQuery.value = 'a'
    expect(filter.isOrderPristine.value).toBe(false)
  })

  it('refuses a drag while maps of several owners are mixed in', async () => {
    const filter = await setup([listed('a', { owner: 'me' }), listed('b', { is_builtin: true })])
    expect(filter.isOrderPristine.value).toBe(false)
  })
})
