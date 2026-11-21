/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, describe, expect, it } from 'vitest'
import { type ShallowRef, computed, nextTick, reactive, ref, shallowRef } from 'vue'

import MapElementIcon from '@/maps/map/elements/components/MapElementIcon.vue'
import {
  type CanvasLineAnchors,
  edgePoint,
  useCanvasLineAnchors
} from '@/maps/map/static/composables/useCanvasLineAnchors'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'

import { aMap, aState, anObject } from '../../../support/fixtures'
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

/** Two hosts drawn 200 apart with a line between them, the icons above their captions. */
function boundLine(states: Readonly<Record<string, ObjectState>> = {}): {
  anchors: CanvasLineAnchors
  line: MapElement
  icons: Record<string, Element>
  config: ShallowRef<MapConfig>
} {
  const canvas = document.createElement('div')
  document.body.append(canvas)
  placeAt(canvas, 0, 0, 1000, 1000)
  const icons: Record<string, Element> = {}
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
    icons[id] = wrapper.querySelector('.maps-map-element-icon')!
    placeAt(icons[id], left, 90, 20, 20)
  }
  const line = anObject({ id: 'l', type: 'line', start_ref: 'a', end_ref: 'b' })
  const config = shallowRef(
    aMap({
      objects: [
        anObject({ id: 'a', type: 'host', x: 110, y: 115 }),
        anObject({ id: 'b', type: 'host', x: 310, y: 115 }),
        line
      ]
    })
  )
  const anchors = useCanvasLineAnchors({
    canvas: shallowRef(canvas),
    config: () => config.value,
    states: () => states,
    dragPositions: () => ({}),
    iconSizes: () => ({ map: 20, override: undefined, fallback: 20 }),
    toMapCoords: (x, y) => ({ x, y }),
    scale: () => ({ sx: 1, sy: 1 }),
    displaySize: ref({ width: 1000, height: 1000 }),
    classic: () => false
  })
  return { anchors, line, icons, config }
}

describe('useCanvasLineAnchors', () => {
  it('aims a bound line at the icon, not at the caption under it', () => {
    const { anchors, line } = boundLine()

    expect(anchors.boundCoordsFor(line)).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })
  })

  it('aims again once a state change has redrawn a bound object', async () => {
    const states = reactive<Record<string, ObjectState>>({})
    const { anchors, line, icons } = boundLine(states)
    const bound = computed(() => anchors.boundCoordsFor(line))
    expect(bound.value).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })

    // The new state draws the icon further left, such as with a wider caption.
    placeAt(icons['b']!, 280, 90, 20, 20)
    states['b'] = aState({ object_id: 'b', type: 'host', state: 'DOWN' })
    await nextTick()

    expect(bound.value).toEqual({ x: 120, y: 100, x2: 280, y2: 100 })
  })

  it('aims no line again while a new state leaves the icons in place', async () => {
    const states = reactive<Record<string, ObjectState>>({})
    const { anchors, line, icons } = boundLine(states)
    let aimed = 0
    const bound = computed(() => {
      aimed++
      return anchors.boundCoordsFor(line)
    })
    expect(bound.value).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })
    let measuredA = 0
    const rectOfA = icons['a']!.getBoundingClientRect
    icons['a']!.getBoundingClientRect = () => {
      measuredA++
      return rectOfA()
    }

    states['b'] = aState({ object_id: 'b', type: 'host', state: 'UP', perf_data: 'rta=0.02ms' })
    await nextTick()

    expect(bound.value).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })
    expect(aimed).toBe(1)
    expect(measuredA).toBe(0)
  })

  it('aims again once a changed map has been drawn', async () => {
    const { anchors, line, icons, config } = boundLine()
    const bound = computed(() => anchors.boundCoordsFor(line))
    expect(bound.value).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })

    // A new caption: the canvas draws before the icon has moved, as a render
    // measures the DOM ahead of patching it.
    config.value = {
      ...config.value,
      objects: config.value.objects.map((object) =>
        object.id === 'b'
          ? {
              ...object,
              label: {
                show: true,
                text: 'B',
                x: 0,
                y: 0,
                size: 10,
                color: '#fff',
                background: 'transparent'
              }
            }
          : object
      )
    }
    expect(bound.value).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })
    placeAt(icons['b']!, 280, 90, 20, 20)
    await nextTick()

    expect(bound.value).toEqual({ x: 120, y: 100, x2: 280, y2: 100 })
  })

  it('aims at an icon drawn after the line', async () => {
    const { anchors, line, icons } = boundLine()
    placeAt(icons['b']!, 0, 0, 0, 0)
    const bound = computed(() => anchors.boundCoordsFor(line))
    // Not laid out yet: the line aims at the object's position, not its icon.
    expect(bound.value.y2).toBeCloseTo(114.25)

    placeAt(icons['b']!, 300, 90, 20, 20)
    await nextTick()

    expect(bound.value).toEqual({ x: 120, y: 100, x2: 300, y2: 100 })
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
      states: () => ({}),
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
