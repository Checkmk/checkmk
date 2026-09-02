/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { dummyT } from 'cmk-ui-library/lib/i18n/i18nDummy'
import { describe, expect, it } from 'vitest'

import { useMapListSort } from '@/maps/home/composables/useMapListSort'
import type { MapRead } from '@/maps/types/api'

import { aListedMap, newMapView } from '../../support/fixtures'

function listed(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, ...over })
}

function sortOf(maps: MapRead[]) {
  return useMapListSort(
    () => maps,
    () => 'me',
    dummyT
  )
}

describe('useMapListSort', () => {
  it('keeps the given order until a column is picked', () => {
    const sort = sortOf([listed('b'), listed('a')])
    expect(sort.sortedMaps.value.map((map) => map.name)).toEqual(['b', 'a'])
    expect(sort.column.value).toBeNull()
  })

  it('sorts by display name, ignoring case', () => {
    const sort = sortOf([listed('b', { alias: 'beta' }), listed('a', { alias: 'Alpha' })])
    sort.toggleColumn('name')
    expect(sort.sortedMaps.value.map((map) => map.name)).toEqual(['a', 'b'])
  })

  it('reverses when the same column is picked again', () => {
    const sort = sortOf([listed('a'), listed('b')])
    sort.toggleColumn('name')
    sort.toggleColumn('name')
    expect(sort.direction.value).toBe('desc')
    expect(sort.sortedMaps.value.map((map) => map.name)).toEqual(['b', 'a'])
  })

  it('starts ascending again on a different column', () => {
    const sort = sortOf([listed('a'), listed('b')])
    sort.toggleColumn('name')
    sort.toggleColumn('name')
    sort.toggleColumn('objects')
    expect(sort.column.value).toBe('objects')
    expect(sort.direction.value).toBe('asc')
  })

  it('sorts a computed map last by object count, having no count to compare', () => {
    const sort = sortOf([
      listed('dynamic', { view: newMapView('flow'), object_count: 0 }),
      listed('placed', { object_count: 3 })
    ])
    sort.toggleColumn('objects')
    expect(sort.sortedMaps.value.map((map) => map.name)).toEqual(['placed', 'dynamic'])
  })

  it('sorts by owner, with your own maps under "You"', () => {
    const sort = sortOf([
      listed('theirs', { owner: 'zoe' }),
      listed('mine', { owner: 'me' }),
      listed('builtin', { is_builtin: true })
    ])
    sort.toggleColumn('owner')
    expect(sort.sortedMaps.value.map((map) => map.name)).toEqual(['builtin', 'mine', 'theirs'])
  })

  it('reports the sort state for assistive technology', () => {
    const sort = sortOf([listed('a')])
    expect(sort.ariaSort('name')).toBe('none')
    sort.toggleColumn('name')
    expect(sort.ariaSort('name')).toBe('ascending')
    expect(sort.ariaSort('type')).toBe('none')
    sort.toggleColumn('name')
    expect(sort.ariaSort('name')).toBe('descending')
  })

  it('does not touch the list it was given', () => {
    const maps = [listed('b'), listed('a')]
    const sort = sortOf(maps)
    sort.toggleColumn('name')
    void sort.sortedMaps.value
    expect(maps.map((map) => map.name)).toEqual(['b', 'a'])
  })
})
