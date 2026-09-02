/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type MockInstance, afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, ref } from 'vue'

import { useMapRotation } from '@/maps/map/composables/useMapRotation'
import type { MapRead } from '@/maps/types/api'

import { fakeMapsServices, mountWithServices } from '../../support/services'

function map(name: string, rotationInterval: number): MapRead {
  return { name, alias: name, rotation_interval: rotationInterval } as MapRead
}

let services: ReturnType<typeof fakeMapsServices>
let store: { maps: { value: MapRead[] }; fetchMaps: MockInstance }
let navigate: MockInstance

// The composable registers lifecycle hooks, so it must run inside a component
// setup; the harness provides the app's services and hands back the returned API.
function mountRotation(mapName: Ref<string>, editMode: Ref<boolean> = ref(false)) {
  const { result: api, unmount } = mountWithServices(services, () =>
    useMapRotation(mapName, editMode)
  )
  return { api, unmount }
}

beforeEach(() => {
  vi.useFakeTimers()
  services = fakeMapsServices()
  store = { maps: services.maps.maps, fetchMaps: vi.spyOn(services.maps, 'fetchMaps') }
  navigate = vi.spyOn(services.nav, 'navigate').mockImplementation(() => {})
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useMapRotation — rotation', () => {
  it('counts down once per second and navigates to the next rotating map', async () => {
    store.maps.value = [map('a', 3), map('b', 5), map('static', 0)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(3)
    expect(api.rotationCountdown.value).toBe(3)

    await vi.advanceTimersByTimeAsync(2000)
    expect(api.rotationCountdown.value).toBe(1)
    expect(navigate).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1000)
    expect(navigate).toHaveBeenCalledWith({ view: 'map', name: 'b' })
    expect(api.rotationCountdown.value).toBe(0)
  })

  it('wraps from the last rotating map back to the first', async () => {
    store.maps.value = [map('a', 3), map('b', 3)]
    const { api } = mountRotation(ref('b'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(navigate).toHaveBeenCalledWith({ view: 'map', name: 'a' })
  })

  it('fetches maps on demand when the store is empty', async () => {
    store.fetchMaps.mockImplementationOnce(async () => {
      store.maps.value = [map('a', 3), map('b', 3)]
    })
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(store.fetchMaps).toHaveBeenCalledOnce()
    expect(navigate).toHaveBeenCalledWith({ view: 'map', name: 'b' })
  })

  it('does not navigate when fewer than two maps rotate', async () => {
    store.maps.value = [map('a', 3), map('static', 0)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(navigate).not.toHaveBeenCalled()
  })

  it('does not start a countdown for a non-positive interval', async () => {
    store.maps.value = [map('a', 3), map('b', 3)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(0)
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(navigate).not.toHaveBeenCalled()
  })
})

describe('useMapRotation — pause and edit mode', () => {
  it('freezes the countdown while paused and resumes after unpausing', async () => {
    store.maps.value = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)

    api.toggleRotationPause()
    expect(api.rotationPaused.value).toBe(true)
    await vi.advanceTimersByTimeAsync(5000)
    expect(api.rotationCountdown.value).toBe(2)
    expect(navigate).not.toHaveBeenCalled()

    api.toggleRotationPause()
    await vi.advanceTimersByTimeAsync(2000)
    expect(navigate).toHaveBeenCalledWith({ view: 'map', name: 'b' })
  })

  it('does not start rotating while in edit mode', async () => {
    store.maps.value = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'), ref(true))
    api.scheduleRotation(2)
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(navigate).not.toHaveBeenCalled()
  })

  it('suspends a running countdown when edit mode is entered', async () => {
    store.maps.value = [map('a', 2), map('b', 2)]
    const editMode = ref(false)
    const { api } = mountRotation(ref('a'), editMode)
    api.scheduleRotation(2)

    editMode.value = true
    await vi.advanceTimersByTimeAsync(5000)
    expect(api.rotationCountdown.value).toBe(2)
    expect(navigate).not.toHaveBeenCalled()

    editMode.value = false
    await vi.advanceTimersByTimeAsync(2000)
    expect(navigate).toHaveBeenCalled()
  })
})

describe('useMapRotation — teardown', () => {
  it('stopRotation cancels the pending navigation and resets the countdown', async () => {
    store.maps.value = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    api.stopRotation()
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(navigate).not.toHaveBeenCalled()
  })

  it('rescheduling replaces the previous timer instead of stacking it', async () => {
    store.maps.value = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    await vi.advanceTimersByTimeAsync(1000)
    api.scheduleRotation(5)
    expect(api.rotationCountdown.value).toBe(5)

    // Were the old timer still alive, navigation would fire after 1 more second.
    await vi.advanceTimersByTimeAsync(1000)
    expect(navigate).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(4000)
    expect(navigate).toHaveBeenCalledOnce()
  })

  it('clears the timer on unmount', async () => {
    store.maps.value = [map('a', 2), map('b', 2)]
    const { api, unmount } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    unmount()
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(navigate).not.toHaveBeenCalled()
  })
})
