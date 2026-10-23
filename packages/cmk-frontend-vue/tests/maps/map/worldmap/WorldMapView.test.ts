/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import { useMapEditor } from '@/maps/map/composables/useMapEditor'
import WorldMapView from '@/maps/map/worldmap/WorldMapView.vue'
import type { MapConfig, WorldmapView } from '@/maps/types/api'

import { aMap, anObject } from '../../support/fixtures'
import { fakeMapsServices, mapsGlobal, runWithServices } from '../../support/services'

const geoView = (view: Partial<WorldmapView> = {}): WorldmapView => ({
  type: 'worldmap',
  lat: 51,
  lng: 10,
  zoom: 5,
  auto_filter_value: '',
  problems_only: false,
  ...view
})

function renderView(
  config: MapConfig,
  {
    canEdit = true,
    autoObjects = 'loaded'
  }: { canEdit?: boolean; autoObjects?: 'none' | 'loading' | 'loaded' | 'failed' } = {}
): void {
  const services = fakeMapsServices()
  services.maps.autoObjects.value = autoObjects
  const editor = runWithServices(services, () => useMapEditor())
  render(WorldMapView, {
    global: mapsGlobal({ WorldMapCanvas: true }, services),
    props: {
      config,
      states: {},
      editor,
      error: null,
      preview: false,
      canEdit,
      checkmkUrl: null,
      filterNeedle: '',
      problemsOnly: false
    }
  })
}

describe('WorldMapView — a map with nothing on it', () => {
  it('shows an editor both ways to fill it', () => {
    renderView(aMap({ view: geoView(), objects: [] }))

    expect(screen.getByText(/No objects yet — click the Edit button/)).toBeInTheDocument()
    expect(screen.getByText(/maps_lat and maps_lng labels/)).toBeInTheDocument()
  })

  it('tells a viewer only that it is empty', () => {
    renderView(aMap({ view: geoView(), objects: [] }), { canEdit: false })

    expect(screen.getByText('This map has no objects yet')).toBeInTheDocument()
  })

  it('says an automap found no hosts once it has answered', () => {
    renderView(aMap({ view: geoView({ auto_source: 'all_hosts' }), objects: [] }))

    expect(screen.getByText(/No hosts with geo coordinates found/)).toBeInTheDocument()
  })

  it('says it is loading while the automap hosts are still to come', () => {
    renderView(aMap({ view: geoView({ auto_source: 'all_hosts' }), objects: [] }), {
      autoObjects: 'loading'
    })

    expect(screen.getByRole('status')).toHaveTextContent('Loading hosts…')
    expect(screen.queryByText(/No hosts with geo coordinates found/)).toBeNull()
  })

  it('says nothing about hosts an automap could not be asked for', () => {
    renderView(aMap({ view: geoView({ auto_source: 'all_hosts' }), objects: [] }), {
      autoObjects: 'failed'
    })

    expect(screen.queryByText(/No hosts with geo coordinates found/)).toBeNull()
  })

  it('says nothing once there is something on the map', () => {
    renderView(aMap({ view: geoView(), objects: [anObject({ id: 'h1', type: 'host' })] }))

    expect(screen.queryByText(/No objects yet/)).toBeNull()
  })
})
