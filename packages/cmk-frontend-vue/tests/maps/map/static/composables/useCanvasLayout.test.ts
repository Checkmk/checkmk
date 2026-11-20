/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { reactive, ref } from 'vue'

import { type CanvasLayout, useCanvasLayout } from '@/maps/map/static/composables/useCanvasLayout'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aMap, aState, anObject, newMapView } from '../../../support/fixtures'

function layoutOf(
  object: MapElement,
  dragPositions = ref<Record<string, { x: number; y: number }>>({}),
  states: Record<string, ObjectState> = {},
  problemsOnly = false
): CanvasLayout {
  const config = aMap({ name: 'test', view: newMapView('static'), objects: [object] })
  return useCanvasLayout({
    config: () => config,
    states: () => states,
    width: () => 1000,
    height: () => 1000,
    filterNeedle: () => undefined,
    problemsOnly: () => problemsOnly,
    editMode: () => false,
    classic: () => false,
    draggingId: () => null,
    dragPositions: () => dragPositions.value
  })
}

describe('useCanvasLayout', () => {
  // A new style would redraw every object whenever the canvas is drawn.
  it('gives an object the same style while it stays where it is', () => {
    const object = anObject({ id: 'web', type: 'host', x: 100, y: 200, host_name: 'web' })
    const layout = layoutOf(object)

    expect(layout.objectStyle(object)).toBe(layout.objectStyle(object))
  })

  it('gives an object a new style once it moves', () => {
    const object = anObject({ id: 'web', type: 'host', x: 100, y: 200, host_name: 'web' })
    const dragPositions = ref<Record<string, { x: number; y: number }>>({})
    const layout = layoutOf(object, dragPositions)
    const before = layout.objectStyle(object)

    dragPositions.value = { web: { x: 300, y: 200 } }

    const after = layout.objectStyle(object)

    expect(after).not.toBe(before)
    expect(after).toMatchObject({ left: '30%', top: '20%' })
  })

  // A state update that shows or hides nothing would otherwise redraw the canvas.
  it('keeps the list of objects shown while the same ones are shown', () => {
    const object = anObject({ id: 'web', type: 'host', x: 100, y: 200, host_name: 'web' })
    const states = reactive<Record<string, ObjectState>>({
      web: aState({ object_id: 'web', type: 'host', state: 'DOWN' })
    })
    const layout = layoutOf(object, undefined, states, true)
    const before = layout.placedObjects.value

    states['web'] = aState({ object_id: 'web', type: 'host', state: 'UNREACHABLE' })

    expect(layout.placedObjects.value).toBe(before)
  })
})
