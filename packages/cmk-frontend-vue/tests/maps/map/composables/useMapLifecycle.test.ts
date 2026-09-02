/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import { useMapLifecycle } from '@/maps/map/composables/useMapLifecycle'

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
})

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
})
