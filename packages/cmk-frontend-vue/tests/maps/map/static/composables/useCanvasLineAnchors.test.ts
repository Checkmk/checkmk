/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, describe, expect, it } from 'vitest'
import { ref, shallowRef } from 'vue'

import MapElementIcon from '@/maps/map/elements/components/MapElementIcon.vue'
import { edgePoint, useCanvasLineAnchors } from '@/maps/map/static/composables/useCanvasLineAnchors'

import { aMap, anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

const BOX = { x: 100, y: 100, halfX: 20, halfY: 10 }

describe('edgePoint', () => {
  it('meets the side the rest of the line is on', () => {
    expect(edgePoint(BOX, 500, 100)).toEqual({ x: 120, y: 100 })
    expect(edgePoint(BOX, -500, 100)).toEqual({ x: 80, y: 100 })
    expect(edgePoint(BOX, 100, 500)).toEqual({ x: 100, y: 110 })
    expect(edgePoint(BOX, 100, -500)).toEqual({ x: 100, y: 90 })
  })

  it('leaves the box by whichever side the ray reaches first', () => {
    // A wide, flat box: a diagonal ray leaves through the top, not the side.
    const point = edgePoint(BOX, 200, 200)
    expect(point.y).toBe(110)
    expect(point.x).toBe(110)
  })

  it('stays at the centre for a line that aims nowhere', () => {
    expect(edgePoint(BOX, 100, 100)).toEqual({ x: 100, y: 100 })
  })
})

afterEach(() => {
  document.body.replaceChildren()
})

// jsdom lays nothing out, so stand in for the browser's measurements.
function placeAt(element: Element, left: number, top: number, width: number, height: number) {
  element.getBoundingClientRect = () => new DOMRect(left, top, width, height)
}

describe('useCanvasLineAnchors', () => {
  it('aims a bound line at the icon, not at the caption under it', () => {
    const canvas = document.createElement('div')
    document.body.append(canvas)
    placeAt(canvas, 0, 0, 1000, 1000)
    // Centred with its caption, an icon sits above its object's position.
    for (const [id, left] of [
      ['a', 100],
      ['b', 300]
    ] as const) {
      const wrapper = document.createElement('div')
      wrapper.dataset['objectId'] = id
      canvas.append(wrapper)
      placeAt(wrapper, left - 10, 90, 40, 50)
      render(MapElementIcon, {
        props: {
          object: anObject({ id, type: 'host', host_name: id }),
          state: undefined,
          iconSize: 20
        },
        container: wrapper,
        global: mapsGlobal()
      })
      placeAt(wrapper.querySelector('.maps-map-element-icon')!, left, 90, 20, 20)
    }
    const line = anObject({ id: 'l', type: 'line', start_ref: 'a', end_ref: 'b' })
    const config = aMap({
      objects: [
        anObject({ id: 'a', type: 'host', x: 110, y: 115 }),
        anObject({ id: 'b', type: 'host', x: 310, y: 115 }),
        line
      ]
    })

    const anchors = useCanvasLineAnchors({
      canvas: shallowRef(canvas),
      config: () => config,
      dragPositions: () => ({}),
      iconSizes: () => ({ map: 20, override: undefined, fallback: 20 }),
      toMapCoords: (x, y) => ({ x, y }),
      scale: () => ({ sx: 1, sy: 1 }),
      displaySize: ref({ width: 1000, height: 1000 }),
      classic: () => false
    })

    expect(anchors.boundCoordsFor(line)).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })
  })

  it('binds no end before the canvas is laid out', () => {
    const line = anObject({ id: 'l', type: 'line', start_ref: 'a', end_ref: 'b' })
    const config = aMap({
      objects: [
        anObject({ id: 'a', type: 'host', x: 100, y: 100 }),
        anObject({ id: 'b', type: 'host', x: 300, y: 100 }),
        line
      ]
    })
    const anchors = useCanvasLineAnchors({
      canvas: shallowRef(null),
      config: () => config,
      dragPositions: () => ({}),
      iconSizes: () => ({ map: 20, override: undefined, fallback: 20 }),
      toMapCoords: (x, y) => ({ x, y }),
      scale: () => ({ sx: 0, sy: 0 }),
      displaySize: ref({ width: 0, height: 0 }),
      classic: () => false
    })

    expect(anchors.boundCoordsFor(line)).toEqual({})
  })
})
