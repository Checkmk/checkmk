/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { useObjectDetailsFetch } from '@/maps/map/detail/composables/useObjectDetailsFetch'
import type { MapElement, ObjectDetails } from '@/maps/types/api'

import { aDetails, anObject } from '../../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../../support/services'

// Lets the fetch and its watchers run before the case looks again.
function settle(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

function aHost(name: string): MapElement {
  return anObject({ id: name, type: 'host', host_name: name })
}

function setup(first: MapElement) {
  const services = fakeMapsServices()
  const replies: { resolve: (d: ObjectDetails) => void; reject: (e: Error) => void }[] = []
  vi.mocked(services.apis.connections.fetchObjectDetails).mockImplementation(
    () => new Promise((resolve, reject) => replies.push({ resolve, reject }))
  )
  const selected = ref(first)
  const { details } = runWithServices(services, () =>
    useObjectDetailsFetch({ object: () => selected.value, connectionId: () => 'local' })
  )
  return { services, replies, selected, details }
}

describe('useObjectDetailsFetch', () => {
  it('keeps the details of the latest selection when an older reply comes late', async () => {
    const { replies, selected, details } = setup(aHost('web01'))
    selected.value = aHost('db01')
    await settle()

    replies[1]!.resolve(aDetails({ type: 'host', host_name: 'db01' }))
    replies[0]!.resolve(aDetails({ type: 'host', host_name: 'web01' }))
    await settle()

    expect(details.value?.host_name).toBe('db01')
  })

  it('keeps the shown details when the reload after a command fails', async () => {
    const { services, replies, details } = setup(aHost('web01'))
    replies[0]!.resolve(aDetails({ type: 'host', host_name: 'web01' }))
    await settle()

    services.states.commandRefreshes.value++
    await settle()
    replies[1]!.reject(new Error('unreachable'))
    await settle()

    expect(details.value?.host_name).toBe('web01')
  })
})
