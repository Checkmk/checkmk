/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { nextTick, reactive, ref } from 'vue'

import type { IconSizes } from '@/maps/map/objectIconSize'
import { useCanvasExtents } from '@/maps/map/static/composables/useCanvasExtents'
import type { MapConfig, MapElement } from '@/maps/types/api'

import { aMap, anObject, newMapView } from '../../../support/fixtures'

/** A map with one object placed well inside the minimum space. */
function mapWith(extra: Partial<MapConfig> = {}): MapConfig {
  return aMap({
    name: 'test',
    view: newMapView('static'),
    objects: [anObject({ id: '1', type: 'host', x: 1000, y: 700, host_name: 'localhost' })],
    ...extra
  })
}

const ICON_SIZES: IconSizes = { map: null, override: undefined, fallback: 60 }

const BACKGROUND = { width: 640, height: 480 }

function extentsOf(
  config: MapConfig,
  backgroundSize: { width: number; height: number } | null = null
): { w: number; h: number } {
  const extents = useCanvasExtents({
    config: () => config,
    backgroundSize: () => backgroundSize,
    iconSizes: () => ICON_SIZES,
    // Only the NagVis-compatible renderer draws the background at its own size.
    classic: () => backgroundSize !== null
  })
  return { w: extents.width.value, h: extents.height.value }
}

/** Moves the map's only object in place, as a drag in the editor does. */
async function extentsAfterMove(
  classic: boolean,
  backgroundSize: { width: number; height: number } | null
): Promise<{ w: number; h: number }> {
  const config = reactive(mapOf(hostAt(100, 100)))
  const extents = useCanvasExtents({
    config: () => config,
    backgroundSize: () => backgroundSize,
    iconSizes: () => ICON_SIZES,
    classic: () => classic
  })

  config.objects[0]!.x = 1000
  await nextTick()

  return { w: extents.width.value, h: extents.height.value }
}

function mapOf(...objects: MapElement[]): MapConfig {
  return mapWith({ objects })
}

function hostAt(x: number, y: number, extra: Partial<MapElement> = {}): MapElement {
  return anObject({ id: '1', type: 'host', x, y, host_name: 'localhost', ...extra })
}

// The coordinate space is the divisor every object's position is a fraction of,
// so a reload has to reuse the one the editor was working with -- otherwise the
// objects re-anchor and the map looks different from the one that was saved.
describe('useCanvasExtents', () => {
  it('derives the space from padded object extents when the map stores none', () => {
    // x=1000 (+150 padding) → 1150; y=700 (+150) → 850.
    expect(extentsOf(mapWith())).toEqual({ w: 1150, h: 850 })
  })

  it('uses a stored size verbatim instead of re-inflating it', () => {
    expect(extentsOf(mapWith({ canvas_width: 1200, canvas_height: 900 }))).toEqual({
      w: 1200,
      h: 900
    })
  })

  it('grows a stored size past an object beyond it, padding included', () => {
    // An object at 1000/700 on a stored 900×600 would sit on the edge.
    expect(extentsOf(mapWith({ canvas_width: 900, canvas_height: 600 }))).toEqual({
      w: 1150,
      h: 850
    })
  })

  // The NagVis-compatible renderer draws at the background's own pixel size.
  it('takes the background size where the renderer draws the background at it', () => {
    expect(extentsOf(mapOf(hostAt(100, 100)), BACKGROUND)).toEqual({ w: 640, h: 480 })
  })

  it('keeps the background size when an object only nears its edge', () => {
    // 560 + 60 stays within 640; 400 + 60 within 480.
    expect(extentsOf(mapOf(hostAt(560, 400)), BACKGROUND)).toEqual({ w: 640, h: 480 })
  })

  // NagVis lets the page grow to the object's end instead of cutting it off.
  it('grows to the end of an icon that crosses the background edge', () => {
    expect(extentsOf(mapOf(hostAt(630, 470)), BACKGROUND)).toEqual({ w: 690, h: 530 })
  })

  it('grows by the image size an object sets', () => {
    const host = hostAt(560, 400, { display: { mode: 'icon', image_size: 128 } })
    expect(extentsOf(mapOf(host), BACKGROUND)).toEqual({ w: 688, h: 528 })
  })

  it('grows to where a line ends, without an icon box', () => {
    const line = anObject({ id: '1', type: 'line', x: 100, y: 100, x2: 700, y2: 470 })
    expect(extentsOf(mapOf(line), BACKGROUND)).toEqual({ w: 700, h: 480 })
  })

  it('grows by the size of a graph beyond the background', () => {
    const graph = anObject({
      id: '1',
      type: 'graph',
      x: 500,
      y: 400,
      graph_width: 300,
      graph_height: 100
    })
    expect(extentsOf(mapOf(graph), BACKGROUND)).toEqual({ w: 800, h: 500 })
  })

  it('grows by the size of a text box beyond the background', () => {
    const textbox = anObject({
      id: '1',
      type: 'textbox',
      x: 600,
      y: 400,
      textbox_width: 100,
      textbox_height: 50
    })
    expect(extentsOf(mapOf(textbox), BACKGROUND)).toEqual({ w: 700, h: 480 })
  })

  // A size stored by the default renderer would leave a blank strip beside the image.
  it('ignores a stored size where the background sets the size', () => {
    const config = mapWith({ canvas_width: 1150, canvas_height: 850, objects: [hostAt(100, 100)] })
    expect(extentsOf(config, BACKGROUND)).toEqual({ w: 640, h: 480 })
  })

  it('starts over at a new background', async () => {
    const background = ref(BACKGROUND)
    const config = mapOf(hostAt(100, 100))
    const extents = useCanvasExtents({
      config: () => config,
      backgroundSize: () => background.value,
      iconSizes: () => ICON_SIZES,
      classic: () => true
    })

    background.value = { width: 320, height: 240 }
    await nextTick()

    expect({ w: extents.width.value, h: extents.height.value }).toEqual({ w: 320, h: 240 })
  })

  it('counts where a line ends against a stored size too', () => {
    const config = mapWith({
      canvas_width: 1200,
      canvas_height: 900,
      objects: [anObject({ id: '1', type: 'line', x: 100, y: 100, x2: 1500, y2: 950 })]
    })
    expect(extentsOf(config)).toEqual({ w: 1650, h: 1100 })
  })

  it('counts where a line ends, not only where it starts', () => {
    const config = mapWith({
      objects: [anObject({ id: '1', type: 'line', x: 10, y: 10, x2: 1000, y2: 700 })]
    })
    expect(extentsOf(config)).toEqual({ w: 1150, h: 850 })
  })

  // The NagVis-compatible canvas is drawn at its pixel size, so growing it
  // moves nothing else.
  it('follows an object moved past the background in the NagVis-compatible renderer', async () => {
    expect(await extentsAfterMove(true, BACKGROUND)).toEqual({ w: 1060, h: 480 })
  })

  it('follows an object moved past the edge of a NagVis map without background', async () => {
    expect(await extentsAfterMove(true, null)).toEqual({ w: 1150, h: 600 })
  })

  it('keeps the space while an object moves in the default renderer', async () => {
    expect(await extentsAfterMove(false, null)).toEqual({ w: 800, h: 600 })
  })
})
