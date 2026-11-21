/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'

import { isGridMemberId } from '@/maps/api/wire'
import { useGridMembers } from '@/maps/map/static/composables/useGridMembers'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aMap, aState, anObject } from '../../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../../support/services'

function member(host: string, state: string, gridId = 'g'): ObjectState {
  return aState({
    object_id: `auto:grid:${gridId}:${host}`,
    type: 'host',
    state,
    host_name: host,
    grid_id: gridId
  })
}

/** The grid's own state when the daemon cut its members at the limit. */
function cutGrid(): ObjectState {
  return aState({ object_id: 'g', type: 'grid', state: 'PENDING', grid_truncated: true })
}

function aGrid(overrides: Partial<MapElement> = {}): MapElement {
  return anObject({ id: 'g', type: 'grid', x: 20, y: 700, ...overrides })
}

function setUp(objects: MapElement[] = [aGrid()]) {
  const services = fakeMapsServices()
  const editing = ref(false)
  services.maps.currentMap.value = aMap({ objects })
  runWithServices(services, () => useGridMembers(() => editing.value))
  const shown = (gridId = 'g') =>
    services.maps.currentMap
      .value!.objects.filter((o) => isGridMemberId(o.id) && o.grid_id === gridId)
      .map((o) => o.host_name)
  const setStates = async (states: ObjectState[]) => {
    services.states.states.value = Object.fromEntries(states.map((s) => [s.object_id, s]))
    await nextTick()
  }
  return { services, editing, shown, setStates }
}

describe('useGridMembers', () => {
  it('lays the members out again when their states change', async () => {
    const { shown, setStates } = setUp([aGrid({ grid_sort: 'state' })])
    await setStates([member('a', 'UP'), member('b', 'UP')])

    await setStates([member('a', 'UP'), member('b', 'DOWN')])

    expect(shown()).toEqual(['b', 'a'])
  })

  it('keeps the object of a member whose place a state change leaves alone', async () => {
    const { services, setStates } = setUp([aGrid({ grid_sort: 'state' })])
    await setStates([member('a', 'DOWN'), member('b', 'UP'), member('c', 'UP')])
    const objectOf = (host: string) =>
      services.maps.currentMap.value!.objects.find((o) => o.host_name === host)
    const before = objectOf('a')

    await setStates([member('a', 'DOWN'), member('b', 'UP'), member('c', 'DOWN')])

    expect(objectOf('a')).toBe(before)
  })

  it('keeps the members of a grid whose states did not change', async () => {
    const { services, setStates } = setUp([aGrid(), aGrid({ id: 'h', x: 400 })])
    await setStates([member('a', 'UP'), member('b', 'UP', 'h')])
    const objectOf = (host: string) =>
      services.maps.currentMap.value!.objects.find((o) => o.host_name === host)
    const before = objectOf('a')

    await setStates([member('a', 'UP'), member('b', 'DOWN', 'h'), member('c', 'UP', 'h')])

    expect(objectOf('a')).toBe(before)
  })

  it('keeps the order while the map is edited and adds new members at the end', async () => {
    const { editing, shown, setStates } = setUp([aGrid({ grid_sort: 'state' })])
    await setStates([member('a', 'UP'), member('b', 'UP')])
    editing.value = true
    await nextTick()

    await setStates([member('a', 'UP'), member('b', 'DOWN'), member('c', 'DOWN')])

    expect(shown()).toEqual(['a', 'b', 'c'])
  })

  it('lays out the grid of another map anew while editing', async () => {
    const { services, editing, setStates } = setUp([aGrid()])
    await setStates([member('a', 'UP'), member('b', 'UP')])
    editing.value = true
    await nextTick()
    const objectOf = (host: string) =>
      services.maps.currentMap.value!.objects.find((o) => o.host_name === host)
    const firstSlot = { x: objectOf('a')!.x, y: objectOf('a')!.y }

    services.maps.currentMap.value = aMap({ name: 'other', objects: [aGrid()] })
    await setStates([member('c', 'UP')])

    expect(objectOf('c')).toMatchObject(firstSlot)
  })

  it('lays a grid whose settings change while the map is edited out anew', async () => {
    const { services, editing, shown, setStates } = setUp([aGrid()])
    await setStates([member('b', 'DOWN'), member('a', 'UP')])
    editing.value = true
    await nextTick()

    services.maps.currentMap.value = {
      ...services.maps.currentMap.value!,
      objects: [aGrid({ grid_sort: 'state', grid_order: 'asc' })]
    }
    await nextTick()

    expect(shown()).toEqual(['b', 'a'])
  })

  it('keeps the order of a grid moved while the map is edited', async () => {
    const { services, editing, shown, setStates } = setUp([aGrid({ grid_sort: 'state' })])
    await setStates([member('a', 'UP'), member('b', 'UP')])
    editing.value = true
    await nextTick()
    await setStates([member('a', 'UP'), member('b', 'DOWN')])

    services.maps.currentMap.value = {
      ...services.maps.currentMap.value!,
      objects: [aGrid({ grid_sort: 'state', x: 200 })]
    }
    await nextTick()

    expect(shown()).toEqual(['a', 'b'])
  })

  it('leaves the slot of a member pinned while the map is edited empty', async () => {
    const { services, editing, setStates } = setUp([aGrid({ grid_per_row: 10 })])
    await setStates([member('a', 'UP'), member('b', 'UP'), member('c', 'UP')])
    editing.value = true
    await nextTick()

    services.maps.currentMap.value = {
      ...services.maps.currentMap.value!,
      objects: [
        ...services.maps.currentMap.value!.objects,
        anObject({ id: 'pinned', type: 'host', host_name: 'a', grid_id: 'g' })
      ]
    }
    await setStates([member('b', 'UP'), member('c', 'UP')])

    expect(
      services.maps.currentMap
        .value!.objects.filter((o) => isGridMemberId(o.id))
        .map((o) => [o.host_name, o.x])
    ).toEqual([
      ['b', 50],
      ['c', 80]
    ])
  })

  it('gives a member joining a cut grid the slot of the one leaving', async () => {
    const { services, shown, setStates } = setUp([aGrid({ grid_per_row: 10 })])
    await setStates([cutGrid(), member('a', 'UP'), member('b', 'UP'), member('c', 'UP')])
    const objectOf = (host: string) =>
      services.maps.currentMap.value!.objects.find((o) => o.host_name === host)
    const c = objectOf('c')

    await setStates([cutGrid(), member('a', 'UP'), member('c', 'UP'), member('d', 'DOWN')])

    expect(shown()).toEqual(['a', 'd', 'c'])
    expect(objectOf('c')).toBe(c)
  })

  it('lays a grid out by name again once it is no longer cut', async () => {
    const { shown, setStates } = setUp([aGrid()])
    await setStates([cutGrid(), member('a', 'UP'), member('b', 'UP'), member('c', 'UP')])
    await setStates([cutGrid(), member('a', 'UP'), member('c', 'UP'), member('d', 'DOWN')])

    await setStates([member('a', 'UP'), member('c', 'UP'), member('d', 'DOWN')])

    expect(shown()).toEqual(['a', 'c', 'd'])
  })

  it('lays a cut grid out anew once the editing ends', async () => {
    const { editing, shown, setStates } = setUp([aGrid()])
    await setStates([cutGrid(), member('b', 'UP'), member('c', 'UP')])
    editing.value = true
    await nextTick()
    await setStates([cutGrid(), member('a', 'DOWN'), member('b', 'UP'), member('c', 'UP')])

    editing.value = false
    await nextTick()

    expect(shown()).toEqual(['a', 'b', 'c'])
  })

  it('leaves out a host pinned out of it before the daemon knows', async () => {
    const { shown, setStates } = setUp([
      aGrid(),
      anObject({ id: 'pinned', type: 'host', host_name: 'a', grid_id: 'g' })
    ])

    await setStates([member('a', 'UP'), member('b', 'UP')])

    expect(shown()).toEqual(['b'])
  })

  it('shows a member again whose pin is taken back', async () => {
    const { services, shown, setStates } = setUp([
      aGrid(),
      anObject({ id: 'pinned', type: 'host', host_name: 'a', grid_id: 'g' })
    ])
    await setStates([member('a', 'UP')])

    services.maps.currentMap.value!.objects = services.maps.currentMap.value!.objects.filter(
      (o) => o.id !== 'pinned'
    )
    await nextTick()

    expect(shown()).toEqual(['a'])
  })

  it('keeps a host the map places elsewhere', async () => {
    const { shown, setStates } = setUp([
      aGrid(),
      anObject({ id: 'placed', type: 'host', host_name: 'a' })
    ])

    await setStates([member('a', 'UP')])

    expect(shown()).toEqual(['a'])
  })

  it('lays out each grid from its own position', async () => {
    const { services, setStates } = setUp([aGrid(), aGrid({ id: 'h', x: 400, y: 100 })])

    await setStates([member('a', 'UP'), member('a', 'UP', 'h')])

    expect(
      services.maps.currentMap
        .value!.objects.filter((o) => isGridMemberId(o.id))
        .map((o) => [o.grid_id, o.x, o.y])
    ).toEqual([
      ['g', 20, 700],
      ['h', 400, 100]
    ])
  })

  it('removes the members of a grid that is deleted', async () => {
    const { services, shown, setStates } = setUp()
    await setStates([member('a', 'UP')])

    services.maps.currentMap.value!.objects = []
    await nextTick()

    expect(shown()).toEqual([])
  })
})
