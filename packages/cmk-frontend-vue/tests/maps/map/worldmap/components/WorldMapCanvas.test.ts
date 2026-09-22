/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import WorldMapCanvas from '@/maps/map/worldmap/components/WorldMapCanvas.vue'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'

import { aMap, aState, anObject, newMapView } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

// Minimal Leaflet stand-in covering exactly what the canvas touches while
// mounting (L.map / tileLayer / divIcon / marker) and unmounting (map.remove).
// jsdom has no layout, so nothing is positioned for real.
//
// A marker's icon element is the one the canvas handed to ``divIcon`` as
// ``html``, and adding the marker puts it into the map container — the contract
// real Leaflet's DivIcon follows, and the one the Vue layer teleports into.
const leaflet = vi.hoisted(() => {
  let mapContainer: HTMLElement | null = null
  const mapStub = {
    on: vi.fn(),
    remove: vi.fn(),
    getPane: vi.fn(() => undefined),
    getContainer: vi.fn(() => mapContainer ?? document.body),
    fitBounds: vi.fn(),
    getCenter: vi.fn(() => ({ lat: 51, lng: 10 })),
    getZoom: vi.fn(() => 5),
    setView: vi.fn(),
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
    invalidateSize: vi.fn(),
    boxZoom: { disable: vi.fn() },
    dragging: { enable: vi.fn(), disable: vi.fn() },
    mouseEventToContainerPoint: vi.fn(() => ({ x: 0, y: 0 })),
    latLngToContainerPoint: vi.fn(() => ({ x: 0, y: 0, distanceTo: () => 0 })),
    containerPointToLatLng: vi.fn(() => ({ lat: 0, lng: 0 }))
  }
  const makeMarker = (_at: unknown, options?: { icon?: { html?: HTMLElement } }) => {
    const element = options?.icon?.html ?? document.createElement('div')
    const marker = {
      on: vi.fn(),
      addTo: vi.fn(() => {
        ;(mapContainer ?? document.body).appendChild(element)
        return marker
      }),
      remove: vi.fn(() => element.remove()),
      setLatLng: vi.fn(),
      setIcon: vi.fn(),
      setZIndexOffset: vi.fn(),
      getLatLng: vi.fn(() => ({ lat: 0, lng: 0 })),
      getElement: vi.fn(() => element),
      dragging: { enable: vi.fn(), disable: vi.fn() }
    }
    return marker
  }
  const makePolyline = () => ({
    on: vi.fn(),
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
    setLatLngs: vi.fn(),
    setStyle: vi.fn(),
    bringToFront: vi.fn(),
    getElement: vi.fn(() => null)
  })
  const makeTileLayer = () => ({
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
    setUrl: vi.fn()
  })
  const L = {
    map: vi.fn((element: HTMLElement) => {
      mapContainer = element
      return mapStub
    }),
    tileLayer: vi.fn(makeTileLayer),
    marker: vi.fn(makeMarker),
    polyline: vi.fn(makePolyline),
    divIcon: vi.fn((options: { html?: HTMLElement }) => options),
    point: vi.fn((x: number, y: number) => ({ x, y, distanceTo: () => 0 })),
    latLngBounds: vi.fn((points: unknown) => points),
    DomEvent: { stopPropagation: vi.fn(), preventDefault: vi.fn() }
  }
  return { L, mapStub }
})

vi.mock('leaflet', () => ({ default: leaflet.L }))

const sampleConfig = (): MapConfig =>
  aMap({
    name: 'geo',
    alias: 'Geo',
    icon_size: 30,
    connection_id: 'test',
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    view: newMapView('worldmap'),
    objects: [
      anObject({
        id: 'h1',
        type: 'host',
        lat: 52.52,
        lng: 13.405,
        host_name: 'berlin-host',
        z: 1
      })
    ]
  })

const sampleStates: Record<string, ObjectState> = {
  h1: aState({
    object_id: 'h1',
    type: 'host',
    state: 'UP',
    output: 'PING OK',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false
  })
}

const baseProps = {
  config: sampleConfig(),
  states: sampleStates,
  editMode: false,
  placing: false,
  picking: false,
  selectedObjectId: null,
  selectedIds: [],
  filterNeedle: '',
  problemsOnly: false,
  preview: false,
  checkmkUrl: null
}

/** Mounts the canvas under a host that records the object-click contract. */
function renderCanvas() {
  const clicked = ref<MapElement | null>(null)
  render(
    defineComponent({
      components: { WorldMapCanvas },
      setup() {
        const props = { ...baseProps, config: sampleConfig() }
        return {
          props,
          onObjectClick: (object: MapElement) => {
            clicked.value = object
          }
        }
      },
      template: `<WorldMapCanvas v-bind="props" @object-click="onObjectClick" />`
    }),
    { global: mapsGlobal() }
  )
  return { clicked }
}

describe('WorldMapCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('mounts a Leaflet map and puts one accessible marker per geo object on it', async () => {
    const { unmount } = render(WorldMapCanvas, {
      global: mapsGlobal(),
      props: { ...baseProps, config: sampleConfig() }
    })
    // The marker's accessible name is "<name>, <state word>", rendered into the
    // marker's element by the Vue layer once the map has been set up.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'berlin-host, Up' })).toBeInTheDocument()
    )

    // Where the marker sits is Leaflet's business and has no representation in
    // the DOM, so the coordinates it was placed at are read off the call.
    expect(leaflet.L.marker).toHaveBeenCalledTimes(1)
    expect(leaflet.L.marker).toHaveBeenCalledWith([52.52, 13.405], expect.anything())
    // The action bar anchors on the object id, so it has to be on the marker.
    const marker = screen.getByRole('button', { name: 'berlin-host, Up' })
    expect(marker.dataset['objectId']).toBe('h1')

    unmount()
    expect(leaflet.mapStub.remove).toHaveBeenCalledTimes(1)
  })

  it('reports a click on a marker as a click on its object', async () => {
    const user = userEvent.setup()
    const { clicked } = renderCanvas()

    await user.click(await screen.findByRole('button', { name: 'berlin-host, Up' }))

    expect(clicked.value).toMatchObject({ id: 'h1', type: 'host', host_name: 'berlin-host' })
  })

  it('reaches the same object without a pointer: focus the marker, press Enter', async () => {
    // Pins the accessibility path: a marker is reachable and activatable by
    // keyboard, which is what makes a geo map operable without a mouse.
    const user = userEvent.setup()
    const { clicked } = renderCanvas()

    const marker = await screen.findByRole('button', { name: 'berlin-host, Up' })
    marker.focus()
    await user.keyboard('{Enter}')

    expect(clicked.value).toMatchObject({ id: 'h1', type: 'host' })
  })

  it('unmounts cleanly even before the async mount setup resolved', async () => {
    const { container, unmount } = render(WorldMapCanvas, {
      global: mapsGlobal(),
      props: { ...baseProps, config: sampleConfig() }
    })
    unmount()
    // A stray rejection or late sync against the torn-down map would fail the
    // test; the container must be empty after unmount.
    await waitFor(() => expect(container.innerHTML).toBe(''))
  })
})
