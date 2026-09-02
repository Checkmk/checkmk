/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'

import { type MapEditor, useMapEditor } from '@/maps/map/composables/useMapEditor'
import type { MapConfig, MapElement } from '@/maps/types/api'

import { fakeMapsServices, runWithServices } from '../../support/services'

function makeObject(o: Partial<MapElement> & { id: string; type: string }): MapElement {
  return o as MapElement
}

// A canvas element whose mouse→map mapping is the identity (rect at origin,
// no native-image dims so the scroll-based branch in _mouseToCanvas applies).
function makeCanvas(): HTMLElement {
  const el = document.createElement('div')
  document.body.appendChild(el)
  el.getBoundingClientRect = () =>
    ({ left: 0, top: 0, width: 1000, height: 1000, right: 1000, bottom: 1000 }) as DOMRect
  return el
}

function mouse(clientX: number, clientY: number): MouseEvent {
  return new MouseEvent('mousedown', { clientX, clientY })
}

describe('useMapEditor line drag — bound endpoints', () => {
  afterEach(() => {
    // End any in-flight drag so the composable tears down its document
    // listeners before the canvas element is removed (avoids a cross-test leak).
    document.dispatchEvent(new MouseEvent('mouseup'))
    document.body.innerHTML = ''
  })

  // Regression: a line bound to an object renders at the object's *live*
  // position (MapCanvas.boundCoordsFor), but the line's stored x/y is only a
  // bind-time fallback. After the object moves, that stored coordinate is stale.
  // Grabbing the line must seed the drag from the live object, not the stale
  // coordinate, or the endpoint snaps wildly across the canvas.
  function mapWithStaleBoundLine(): MapConfig {
    const host = makeObject({ id: 'host1', type: 'host', x: 500, y: 400 })
    const line = makeObject({
      id: 'line1',
      type: 'line',
      // Stale bind-time coordinate — the host has since moved to (500, 400).
      x: 200,
      y: 100,
      x2: 700,
      y2: 600,
      start_ref: 'host1',
      end_ref: null
    })
    return { objects: [host, line] } as unknown as MapConfig
  }

  it('seeds a move drag of a bound line from the live object, not the stale stored coord', () => {
    const services = fakeMapsServices()
    const map = mapWithStaleBoundLine()
    services.maps.currentMap.value = map
    const editor = runWithServices(services, () => useMapEditor())
    const line = map.objects.find((o) => o.id === 'line1')!

    editor.startLineDrag(mouse(300, 300), line, 'move', makeCanvas(), null)

    const seeded = editor.lineDragPositions['line1']!
    expect(seeded.x).toBe(500) // live host x, not stale 200
    expect(seeded.y).toBe(400) // live host y, not stale 100
  })

  it('keeps the bound endpoint glued to the live object while the line is moved', () => {
    const services = fakeMapsServices()
    const map = mapWithStaleBoundLine()
    services.maps.currentMap.value = map
    const editor = runWithServices(services, () => useMapEditor())
    const line = map.objects.find((o) => o.id === 'line1')!

    editor.startLineDrag(mouse(300, 300), line, 'move', makeCanvas(), null)
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 360, clientY: 320 }))

    const dragged = editor.lineDragPositions['line1']!
    // Bound start stays on the host; the free end follows the cursor delta.
    expect(dragged.x).toBe(500)
    expect(dragged.y).toBe(400)
    expect(dragged.x2).toBe(760) // 700 + 60
    expect(dragged.y2).toBe(620) // 600 + 20
  })

  it('seeds a start-handle drag of a bound endpoint from the live object', () => {
    const services = fakeMapsServices()
    const map = mapWithStaleBoundLine()
    services.maps.currentMap.value = map
    const editor = runWithServices(services, () => useMapEditor())
    const line = map.objects.find((o) => o.id === 'line1')!

    editor.startLineDrag(mouse(300, 300), line, 'start', makeCanvas(), null)

    const seeded = editor.lineDragPositions['line1']!
    expect(seeded.x).toBe(500)
    expect(seeded.y).toBe(400)
  })
})

// Regression: placing runs from a canvas click, long after the component that
// called ``useMapEditor`` finished setting up. Anything the placement path
// injects has to be resolved at setup time — a ``useSettings()`` inside
// ``placeAt`` throws "no provider for MapsServices" and the object never lands.
describe('useMapEditor placing — services resolved outside setup', () => {
  const emptyMap = () => ({ objects: [] }) as unknown as MapConfig

  it('places a host from a canvas click after setup has finished', async () => {
    const services = fakeMapsServices()
    const map = emptyMap()
    services.maps.currentMap.value = map
    const editor = runWithServices(services, () => useMapEditor())

    editor.draft.type = 'host'
    editor.draft.host_name = 'heute'
    editor.startPlacing()
    await editor.placeAt(120, 80)

    expect(map.objects).toHaveLength(1)
    expect(map.objects[0]).toMatchObject({ type: 'host', host_name: 'heute', x: 120, y: 80 })
  })

  it('places a geo object from a map click after setup has finished', async () => {
    const services = fakeMapsServices()
    const map = emptyMap()
    services.maps.currentMap.value = map
    const editor = runWithServices(services, () => useMapEditor())

    editor.draft.type = 'host'
    editor.draft.host_name = 'heute'
    editor.startPlacing()
    await editor.placeAtLatLng(48.1, 11.6)

    expect(map.objects).toHaveLength(1)
    expect(map.objects[0]).toMatchObject({ type: 'host', lat: 48.1, lng: 11.6 })
  })
})
// The server stamps the linked map's title onto every object it serves, so a
// link the operator re-points in the editor would keep captioning itself with
// the previous target until the map is loaded again.
describe('useMapEditor map links — the caption follows the target', () => {
  function editorWithLink(): { link: MapElement; editor: MapEditor } {
    const services = fakeMapsServices()
    const link = makeObject({
      id: 'link1',
      type: 'map',
      map_name: 'dc_1',
      map_title: 'Datacenter 1'
    })
    services.maps.currentMap.value = { objects: [link] } as unknown as MapConfig
    services.maps.maps.value = [
      { name: 'dc_1', alias: 'Datacenter 1' },
      { name: 'dc_2', alias: 'Datacenter 2' }
    ] as typeof services.maps.maps.value
    return {
      link,
      editor: runWithServices(services, () => useMapEditor())
    }
  }

  it('re-stamps the title when the link is pointed at another map', () => {
    const { link, editor } = editorWithLink()

    editor.updateObjectProperties('link1', { map_name: 'dc_2' })

    expect(link.map_title).toBe('Datacenter 2')
  })

  it('drops the title where the new target is none the operator can see', () => {
    const { link, editor } = editorWithLink()

    editor.updateObjectProperties('link1', { map_name: 'private_map' })

    expect(link.map_title).toBeNull()
  })
})
