/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import { useObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'

import { aMap } from '../../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../../support/services'

describe('useObjectSuggestions – maps', () => {
  it('leaves out the map being edited: a link to itself goes nowhere', () => {
    const services = fakeMapsServices()
    services.maps.currentMap.value = aMap({ name: 'here' })
    services.maps.maps.value = [
      { name: 'here', alias: 'This map' },
      { name: 'all_hosts', alias: 'Host radar' }
    ] as typeof services.maps.maps.value

    const suggestions = runWithServices(services, () =>
      useObjectSuggestions({
        connectionId: () => 'test',
        objectType: () => 'map',
        hostName: () => ''
      })
    )

    expect(suggestions.maps.items.value).toEqual([{ name: 'all_hosts', title: 'Host radar' }])
  })

  it('keeps a self-link that is already stored, so the field still shows it', () => {
    // A legacy import can leave a map-link pointing at its own map. Dropping it
    // from the list would make the dropdown resolve the value to nothing and
    // read as "No other maps available" over a binding that is set.
    const services = fakeMapsServices()
    services.maps.currentMap.value = aMap({ name: 'here' })
    services.maps.maps.value = [
      { name: 'here', alias: 'This map' },
      { name: 'all_hosts', alias: 'Host radar' }
    ] as typeof services.maps.maps.value

    const suggestions = runWithServices(services, () =>
      useObjectSuggestions({
        connectionId: () => 'test',
        objectType: () => 'map',
        hostName: () => '',
        mapName: () => 'here'
      })
    )

    expect(suggestions.maps.items.value.map((entry) => entry.name)).toEqual(['here', 'all_hosts'])
  })
})

describe('useObjectSuggestions – services', () => {
  it('drops the lookup the cleared host left in flight', async () => {
    // Clearing the host empties the list; the answer still on its way for that
    // host must not refill it under a field that now names no host at all.
    const services = fakeMapsServices()
    let answer: (names: string[]) => void = () => {}
    const inFlight = new Promise<string[]>((resolve) => {
      answer = resolve
    })
    vi.mocked(services.apis.objects.fetchObjects).mockImplementation(async (objectType: string) =>
      objectType === 'service' ? inFlight : []
    )

    const hostName = ref('web-01')
    const suggestions = runWithServices(services, () =>
      useObjectSuggestions({
        connectionId: () => 'test',
        objectType: () => 'service',
        hostName: () => hostName.value
      })
    )

    hostName.value = ''
    await nextTick()
    answer(['CPU load'])
    await nextTick()

    expect(suggestions.services.items.value).toEqual([])
    expect(suggestions.services.loading.value).toBe(false)
  })
})
