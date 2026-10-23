/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useMapViewState } from '@/maps/map/composables/useMapViewState'
import type { MapsServices } from '@/maps/services/context'
import type { MapConfig } from '@/maps/types/api'

import { aListedMap } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

/** The choices are held on the map service, so each case gets a fresh set. */
function aMap(name: string): MapConfig {
  return {
    name,
    alias: name,
    view: { type: 'static' }
  } as MapConfig
}

function openMap(config: MapConfig, canEdit: boolean, preview = false): MapsServices {
  const services = fakeMapsServices()
  services.maps.maps.value = [aListedMap({ name: config.name, can_edit: canEdit })]
  services.maps.currentMap.value = config
  services.nav.state.preview = preview
  return services
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useMapViewState — a map that can be saved', () => {
  it('writes the chosen drawing into the map and saves it', () => {
    const config = { ...aMap('writable-saves'), view: { type: 'foldertree' } } as MapConfig
    const services = openMap(config, true)

    const state = runWithServices(services, () => useMapViewState())
    state.folderView.value = 'list'

    expect(config.view).toMatchObject({ default_view: 'list' })
    vi.advanceTimersByTime(400)
    expect(services.apis.mapConfig.update).toHaveBeenCalled()
  })

  // A published map shows every viewer what its settings say, not what the
  // last editor happened to filter while reading it.
  it('keeps the problems filter to the viewer', () => {
    const config = aMap('writable-filter')
    const services = openMap(config, true)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(state.problemsOnly.value).toBe(true)
    expect(config.view).toEqual({ type: 'static' })
    vi.advanceTimersByTime(400)
    expect(services.apis.mapConfig.update).not.toHaveBeenCalled()
  })

  it('starts from the problems filter the map was saved with', () => {
    const config = { ...aMap('writable-default'), view: { type: 'static', problems_only: true } }
    const services = openMap(config as MapConfig, true)

    const state = runWithServices(services, () => useMapViewState())

    expect(state.problemsOnly.value).toBe(true)
  })
})

describe('useMapViewState — the saved problems filter changes', () => {
  it('shows the newly saved filter over a choice made before it', () => {
    const config = aMap('writable-resaved')
    const services = openMap(config, true)
    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true
    state.problemsOnly.value = false

    config.view = { type: 'static', problems_only: true }

    expect(state.problemsOnly.value).toBe(true)
  })
})

describe('useMapViewState — a map the user may not edit', () => {
  it('shows the problems filter the operator switched on', () => {
    const services = openMap(aMap('held-problems'), false)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(state.problemsOnly.value).toBe(true)
  })

  it('leaves the stored map untouched', () => {
    const config = aMap('held-unwritten')
    const services = openMap(config, false)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(config.view).toEqual({ type: 'static' })
    vi.advanceTimersByTime(400)
    expect(services.apis.mapConfig.update).not.toHaveBeenCalled()
  })

  it('agrees with a second holder of the state on the same map', () => {
    const services = openMap(aMap('held-two-holders'), false)

    const { drawing, shell } = runWithServices(services, () => ({
      drawing: useMapViewState(),
      shell: useMapViewState()
    }))
    drawing.problemsOnly.value = true

    expect(shell.problemsOnly.value).toBe(true)
  })

  it('does not carry the choice over to the next map', () => {
    const services = openMap(aMap('held-first'), false)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true
    services.maps.currentMap.value = aMap('held-second')

    expect(state.problemsOnly.value).toBe(false)
  })
})

describe('useMapViewState — a folder tree the user may not edit', () => {
  /** The drawing switch is the control an operator reaches for first, and every
   *  built-in map is one the user may not edit. */
  it('shows the drawing the operator chose', () => {
    const config = { ...aMap('held-drawing'), view: { type: 'foldertree' } } as MapConfig
    const services = openMap(config, false)

    const state = runWithServices(services, () => useMapViewState())
    state.folderView.value = 'list'

    expect(state.folderView.value).toBe('list')
    expect(config.view).toEqual({ type: 'foldertree' })
  })
})

describe('useMapViewState — the settings preview', () => {
  it('neither saves the choice nor holds it, because the map is thrown away with the dialog', () => {
    const config = aMap('preview-map')
    const services = openMap(config, true, true)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(config.view).toEqual({ type: 'static' })
    expect(state.problemsOnly.value).toBe(false)
  })
})
