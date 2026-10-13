/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { computed, defineComponent, h, ref } from 'vue'

import { useCanvasDrag } from '@/maps/map/presentation/composables/useCanvasDrag'
import { useCanvasSelection } from '@/maps/map/presentation/composables/useCanvasSelection'
import { createElement } from '@/maps/map/presentation/elements'
import type { PresentationElement } from '@/maps/types/api'

function data(x: number, y: number, w = 100, h = 100): PresentationElement {
  return Object.assign(createElement('data', x, y), { w, h })
}

/** A pointer-down as the canvas passes it on: only the coordinates matter. */
function pointerDown(clientX: number, clientY: number): PointerEvent {
  return {
    clientX,
    clientY,
    pointerId: 1,
    target: document.createElement('div')
  } as unknown as PointerEvent
}

/**
 * The drag composable inside a mounted component -- it follows the gesture on
 * ``window``, and those listeners are bound on mount. The slide is in screen
 * coordinates 1:1 so a gesture reads as slide units.
 */
function setup(initial: PresentationElement[]) {
  const elements = ref<PresentationElement[]>(initial)
  const byId = (id: string | null | undefined): PresentationElement | undefined =>
    id ? elements.value.find((el) => el.id === id) : undefined
  const selection = useCanvasSelection({
    elements: computed(() => elements.value),
    byId,
    topLevelId: (id) => id,
    isGrouped: () => false,
    isLocked: () => false
  })

  let drag!: ReturnType<typeof useCanvasDrag>
  render(
    defineComponent({
      setup() {
        drag = useCanvasDrag({
          elements,
          byId,
          isGrouped: () => false,
          selection,
          screenToSlide: (clientX, clientY) => ({ x: clientX, y: clientY }),
          snapshot: vi.fn(),
          scheduleSave: vi.fn()
        })
        return () => h('div')
      }
    })
  )

  const moveTo = (clientX: number, clientY: number): void => {
    window.dispatchEvent(new MouseEvent('pointermove', { clientX, clientY }))
  }
  return { selection, drag, moveTo }
}

describe('useCanvasDrag', () => {
  it('snaps the element the pointer grabbed, not the first of the selection', () => {
    const first = data(0, 0)
    const grabbed = data(490, 0)
    const neighbour = data(500, 300)
    const { selection, drag, moveTo } = setup([first, grabbed, neighbour])
    selection.select(first.id)
    selection.toggle(grabbed.id)

    drag.beginMove(grabbed.id, pointerDown(0, 0))
    moveTo(7, 0)

    // 490 + 7 is within the snap threshold of the neighbour's left edge.
    expect(grabbed.x).toBe(500)
    // The rest of the selection follows the same, snapped delta.
    expect(first.x).toBe(10)
  })

  it('moves the whole selection when the grabbed element carries no snap', () => {
    const first = data(0, 0)
    const grabbed = data(490, 0)
    const { selection, drag, moveTo } = setup([first, grabbed])
    selection.select(first.id)
    selection.toggle(grabbed.id)

    drag.beginMove(grabbed.id, pointerDown(0, 0))
    moveTo(40, 25)

    expect({ x: grabbed.x, y: grabbed.y }).toEqual({ x: 530, y: 25 })
    expect({ x: first.x, y: first.y }).toEqual({ x: 40, y: 25 })
  })
})
