/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import { useMapLifecycle } from '@/maps/map/composables/useMapLifecycle'
import type { MapElement } from '@/maps/types/api'

import { aMap, aMapAccess, anObject } from '../../support/fixtures'
import { fakeMapsServices, mountWithServices } from '../../support/services'

let services: ReturnType<typeof fakeMapsServices>

const SIGNED = { config_b64: 'x', sig: 'y' }

/** A fetch per map name, resolved by the case in the order it wants. */
function deferredFetches(): { resolve: (name: string) => void } {
  const pending = new Map<string, () => void>()
  vi.spyOn(services.maps, 'fetchMap').mockImplementation(
    (name, onSigned) =>
      new Promise<void>((done) =>
        pending.set(name, () => {
          onSigned?.(SIGNED)
          done()
        })
      )
  )
  return {
    resolve: (name: string) => {
      const done = pending.get(name)
      if (!done) {
        throw new Error(`no pending fetch for ${name}`)
      }
      done()
    }
  }
}

function mountLifecycle(mapName: Ref<string>) {
  return mountWithServices(services, () =>
    useMapLifecycle({
      mapName: () => mapName.value,
      onMapChanged: () => {},
      rotation: { stop: () => {}, schedule: () => {} }
    })
  )
}

beforeEach(() => {
  services = fakeMapsServices()
  vi.spyOn(services.maps, 'fetchMap').mockImplementation(async (_name, onSigned) => {
    onSigned?.(SIGNED)
  })
  vi.spyOn(services.states, 'connectToMap').mockResolvedValue(undefined)
  vi.spyOn(services.states, 'disconnect').mockImplementation(() => {})
  vi.spyOn(services.maps, 'flushSave').mockResolvedValue(undefined)
  vi.spyOn(services.maps, 'loadAutoObjects').mockResolvedValue(undefined)
  vi.spyOn(services.states, 'reregister').mockResolvedValue(undefined)
})

function deferredConnect(): { resolve: () => void; reject: (error: Error) => void } {
  let settle: { resolve: () => void; reject: (error: Error) => void } | null = null
  vi.spyOn(services.states, 'connectToMap').mockImplementation(
    () => new Promise<void>((resolve, reject) => (settle = { resolve, reject }))
  )
  return {
    resolve: () => settle!.resolve(),
    reject: (error: Error) => settle!.reject(error)
  }
}

async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

describe('useMapLifecycle', () => {
  it('opens the state stream for the map it fetched', async () => {
    const fetches = deferredFetches()
    mountLifecycle(ref('dc1'))

    fetches.resolve('dc1')
    await nextTick()

    expect(services.states.connectToMap).toHaveBeenCalledWith('dc1', SIGNED)
  })

  it('lets go of the map it leaves before the next one loads', async () => {
    deferredFetches()
    const mapName = ref('left')
    mountLifecycle(mapName)
    await nextTick()
    vi.mocked(services.states.disconnect).mockClear()

    mapName.value = 'next'
    await nextTick()

    expect(services.states.disconnect).toHaveBeenCalledOnce()
  })

  it('connects no map that could not be loaded', async () => {
    vi.spyOn(services.maps, 'fetchMap').mockResolvedValue(undefined)
    mountLifecycle(ref('gone'))
    await settle()

    expect(services.states.connectToMap).not.toHaveBeenCalled()
  })

  // Rotation and object clicks both swap the name under the same component,
  // so a slow fetch can resolve after a faster one for another map.
  it('does not open a stream for a map that has since been left', async () => {
    const fetches = deferredFetches()
    const mapName = ref('slow')
    mountLifecycle(mapName)

    mapName.value = 'fast'
    await nextTick()
    fetches.resolve('fast')
    await nextTick()
    fetches.resolve('slow')
    await nextTick()

    expect(services.states.connectToMap).toHaveBeenCalledTimes(1)
    expect(services.states.connectToMap).toHaveBeenCalledWith('fast', SIGNED)
  })

  // The daemon inflates the auto-source hosts from the config it was handed,
  // so asking before the connect registered the map comes back empty.
  it('loads the auto-source hosts once the map is connected', async () => {
    const connect = deferredConnect()
    mountLifecycle(ref('world'))
    await settle()

    expect(services.maps.loadAutoObjects).not.toHaveBeenCalled()

    connect.resolve()
    await settle()

    expect(services.maps.loadAutoObjects).toHaveBeenCalledWith('world', true)
  })

  it('does not load the auto-source hosts of a map that has since been left', async () => {
    const connect = deferredConnect()
    const mapName = ref('world')
    mountLifecycle(mapName)
    await settle()

    mapName.value = 'other'
    await nextTick()
    connect.resolve()
    await settle()

    expect(services.maps.loadAutoObjects).not.toHaveBeenCalledWith('world')
  })

  it('gives up on the auto-source hosts when the connect failed', async () => {
    const connect = deferredConnect()
    mountLifecycle(ref('world'))
    await settle()

    connect.reject(new Error('Maps daemon unreachable'))
    await settle()

    expect(services.maps.loadAutoObjects).toHaveBeenCalledWith('world', false)
  })

  it('reports auto-source hosts that could not be loaded', async () => {
    vi.spyOn(services.maps, 'loadAutoObjects').mockRejectedValue(new Error('Map not found'))
    const error = vi.spyOn(services.toasts, 'error').mockImplementation(() => {})
    mountLifecycle(ref('world'))

    await settle()

    expect(error).toHaveBeenCalledWith('Map not found')
  })

  it('does not re-register the map for its auto-source hosts', async () => {
    vi.spyOn(services.maps, 'fetchMap').mockResolvedValue(undefined)
    services.maps.currentMapAccess.value = aMapAccess()
    services.maps.currentMap.value = aMap({
      name: 'world',
      objects: [anObject({ id: 'core', type: 'host' })]
    })
    mountLifecycle(ref('world'))
    await settle()

    services.maps.currentMap.value!.objects.push(anObject({ id: 'auto:db01', type: 'host' }))
    await settle()

    expect(services.states.reregister).not.toHaveBeenCalled()
  })

  it('re-registers the map when a dynamic group is given another filter', async () => {
    vi.spyOn(services.maps, 'fetchMap').mockResolvedValue(undefined)
    services.maps.currentMapAccess.value = aMapAccess()
    services.maps.currentMap.value = aMap({
      name: 'groups',
      objects: [anObject({ id: 'g1', type: 'dyngroup', object_types: 'host', object_filter: null })]
    })
    mountLifecycle(ref('groups'))
    await settle()

    services.maps.currentMap.value!.objects[0]!.object_filter = 'Filter: name = db01'
    await settle()

    expect(services.states.reregister).toHaveBeenCalledOnce()
  })

  it('does not re-register the map of a user who may not edit it', async () => {
    vi.spyOn(services.maps, 'fetchMap').mockResolvedValue(undefined)
    services.maps.currentMapAccess.value = aMapAccess({ can_edit: false })
    services.maps.currentMap.value = aMap({
      name: 'groups',
      objects: [anObject({ id: 'g1', type: 'dyngroup', object_types: 'host', object_filter: null })]
    })
    mountLifecycle(ref('groups'))
    await settle()

    services.maps.currentMap.value!.objects.push(anObject({ id: 'h1', type: 'host' }))
    await settle()

    expect(services.states.reregister).not.toHaveBeenCalled()
  })

  it.each([
    ['given another precision', (bundle: MapElement) => (bundle.bundle_precision = 2)],
    ['moved', (bundle: MapElement) => (bundle.lat = 51)]
  ])('re-registers the map when a location bundle is %s', async (_case, edit) => {
    vi.spyOn(services.maps, 'fetchMap').mockResolvedValue(undefined)
    services.maps.currentMapAccess.value = aMapAccess()
    services.maps.currentMap.value = aMap({
      name: 'world',
      objects: [anObject({ id: 'b1', type: 'dyngroup', bundle_kind: 'location', lat: 50, lng: 8 })]
    })
    mountLifecycle(ref('world'))
    await settle()

    edit(services.maps.currentMap.value!.objects[0]!)
    await settle()

    expect(services.states.reregister).toHaveBeenCalledOnce()
  })

  it('does not re-register the map for a moved object', async () => {
    vi.spyOn(services.maps, 'fetchMap').mockResolvedValue(undefined)
    services.maps.currentMapAccess.value = aMapAccess()
    services.maps.currentMap.value = aMap({
      name: 'groups',
      objects: [anObject({ id: 'g1', type: 'dyngroup', object_types: 'host' })]
    })
    mountLifecycle(ref('groups'))
    await settle()

    services.maps.currentMap.value!.objects[0]!.x = 300
    await settle()

    expect(services.states.reregister).not.toHaveBeenCalled()
  })
})
