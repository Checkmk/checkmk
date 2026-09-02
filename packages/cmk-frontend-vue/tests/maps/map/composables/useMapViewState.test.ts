/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useMapViewState } from '@/maps/map/composables/useMapViewState'
import type { MapsServices } from '@/maps/services/context'
import type { MapConfig } from '@/maps/types/api'

import { fakeMapsServices, runWithServices } from '../../support/services'

/** The choices are held on the map service, so each case gets a fresh set. */
function aMap(name: string, readonly: boolean): MapConfig {
  return {
    name,
    alias: name,
    readonly,
    view: { type: 'static' }
  } as MapConfig
}

function openMap(config: MapConfig, preview = false): MapsServices {
  const services = fakeMapsServices()
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
  it('writes the chosen filter into the map and saves it', () => {
    const config = aMap('writable-saves', false)
    const services = openMap(config)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(config.view).toMatchObject({ problems_only: true })
    vi.advanceTimersByTime(400)
    expect(services.apis.mapConfig.update).toHaveBeenCalled()
  })
})

describe('useMapViewState — a read-only map', () => {
  it('shows the problems filter the operator switched on', () => {
    const services = openMap(aMap('readonly-problems', true))

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(state.problemsOnly.value).toBe(true)
  })

  it('leaves the stored map untouched', () => {
    const config = aMap('readonly-unwritten', true)
    const services = openMap(config)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(config.view).toEqual({ type: 'static' })
    vi.advanceTimersByTime(400)
    expect(services.apis.mapConfig.update).not.toHaveBeenCalled()
  })

  it('agrees with a second holder of the state on the same map', () => {
    const services = openMap(aMap('readonly-two-holders', true))

    const { drawing, shell } = runWithServices(services, () => ({
      drawing: useMapViewState(),
      shell: useMapViewState()
    }))
    drawing.problemsOnly.value = true

    expect(shell.problemsOnly.value).toBe(true)
  })

  it('does not carry the choice over to the next map', () => {
    const services = openMap(aMap('readonly-first', true))

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true
    services.maps.currentMap.value = aMap('readonly-second', true)

    expect(state.problemsOnly.value).toBe(false)
  })
})

describe('useMapViewState — the settings preview', () => {
  it('neither saves the choice nor holds it, because the map is thrown away with the dialog', () => {
    const config = aMap('preview-map', false)
    const services = openMap(config, true)

    const state = runWithServices(services, () => useMapViewState())
    state.problemsOnly.value = true

    expect(config.view).toEqual({ type: 'static' })
    expect(state.problemsOnly.value).toBe(false)
  })
})
