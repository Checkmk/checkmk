/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import { useMapLifecycle } from '@/maps/map/composables/useMapLifecycle'

import { aMap, anObject } from '../../support/fixtures'
import { fakeMapsServices, mountWithServices } from '../../support/services'

let services: ReturnType<typeof fakeMapsServices>

/** A fetch per map name, resolved by the case in the order it wants. */
function deferredFetches(): { resolve: (name: string) => void } {
  const pending = new Map<string, () => void>()
  vi.spyOn(services.maps, 'fetchMap').mockImplementation(
    (name: string) => new Promise<void>((done) => pending.set(name, done))
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

    expect(services.states.connectToMap).toHaveBeenCalledWith('dc1', undefined)
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
    expect(services.states.connectToMap).toHaveBeenCalledWith('fast', undefined)
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
})
