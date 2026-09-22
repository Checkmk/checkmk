/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type MockInstance, afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { useSlideDocument } from '@/maps/map/presentation/composables/useSlideDocument'
import { createElement } from '@/maps/map/presentation/elements'
import type { MapConfig, PresentationView } from '@/maps/types/api'

import { newMapView } from '../../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../../support/services'

/**
 * The composable persists by writing the working view into the maps service's
 * currentMap and triggering its debounced whole-map save, so the app's own
 * services are provided and the two calls are observed on them.
 */
let services: ReturnType<typeof fakeMapsServices>
let maps: { scheduleSave: MockInstance; flushSave: MockInstance }
let states: { refresh: MockInstance }

function withDoc(): ReturnType<typeof useSlideDocument> {
  return runWithServices(services, () => useSlideDocument(makeConfig))
}

/** The presentation view as the store holds it while the slide is edited. */
function storedView(): PresentationView {
  return services.maps.currentMap.value!.view as PresentationView
}

function makeConfig(): MapConfig {
  const view: PresentationView = { ...newMapView('presentation'), elements: [] } as PresentationView
  return { name: 'pres1', alias: 'P', connection_id: 'live_1', version: 3, view } as MapConfig
}

describe('useSlideDocument', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    services = fakeMapsServices()
    services.maps.currentMap.value = makeConfig()
    maps = {
      scheduleSave: vi.spyOn(services.maps, 'scheduleSave').mockImplementation(() => {}),
      flushSave: vi.spyOn(services.maps, 'flushSave').mockResolvedValue(undefined)
    }
    states = { refresh: vi.spyOn(services.states, 'refresh').mockResolvedValue(undefined) }
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('mutate records a history step; undo restores elements and theme together', () => {
    const doc = withDoc()
    const el = createElement('rect', 10, 10)

    doc.mutate(() => {
      doc.local.value = { ...doc.local.value, theme: 'ops', elements: [el] }
    })
    expect(doc.elements.value).toHaveLength(1)
    expect(doc.local.value.theme).toBe('ops')

    doc.undo()
    expect(doc.elements.value).toHaveLength(0)
    expect(doc.local.value.theme).toBe('midnight')

    doc.redo()
    expect(doc.elements.value).toHaveLength(1)
    expect(doc.local.value.theme).toBe('ops')
  })

  // Holding the edit back here would put it out of reach of the store's flush,
  // so leaving the map inside a debounce window would drop it.
  it('hands every mutation to the store at once instead of debouncing it again', () => {
    const doc = withDoc()

    doc.mutate(() => doc.setElements([createElement('rect', 0, 0)]))
    expect(maps.scheduleSave).toHaveBeenCalledTimes(1)
    expect(storedView().elements).toHaveLength(1)

    doc.mutate(() => doc.setElements([...doc.elements.value, createElement('text', 0, 0)]))
    expect(maps.scheduleSave).toHaveBeenCalledTimes(2)
    expect(storedView().elements).toHaveLength(2)
  })

  it('refreshes states once a burst of edits settles, not per edit', async () => {
    const doc = withDoc()

    doc.mutate(() => doc.setElements([createElement('rect', 0, 0)]))
    doc.mutate(() => doc.setElements([...doc.elements.value, createElement('text', 0, 0)]))
    expect(states.refresh).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(500)
    expect(states.refresh).toHaveBeenCalledTimes(1)
  })

  it('reports a rejected save rather than claiming the slide was stored', async () => {
    const doc = withDoc()
    maps.flushSave.mockImplementation(async () => {
      services.maps.saving.value = true
      await nextTick()
      services.maps.error.value = 'boom'
      services.maps.saving.value = false
      await nextTick()
    })

    await doc.saveNow()
    await nextTick()
    expect(doc.saveLabel.value).toBe('Not saved')
  })

  it('reports a stored slide once the store answers', async () => {
    const doc = withDoc()
    maps.flushSave.mockImplementation(async () => {
      services.maps.saving.value = true
      await nextTick()
      services.maps.saving.value = false
      await nextTick()
    })

    await doc.saveNow()
    await nextTick()
    expect(doc.saveLabel.value).toBe('Saved')
  })

  it('exposes shared lookups (byId, topLevelId, nextZ)', () => {
    const doc = withDoc()
    const a = createElement('rect', 0, 0)
    a.z = 5
    const group = createElement('rect', 0, 0)
    doc.setElements([a])
    expect(doc.byId(a.id)?.id).toBe(a.id)
    expect(doc.byId(undefined)).toBeUndefined()
    expect(doc.topLevelId(a.id)).toBe(a.id)
    expect(doc.nextZ.value).toBe(6)
    expect(doc.byId(group.id)).toBeUndefined()
  })
})
