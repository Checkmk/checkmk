/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, ref } from 'vue'

import { useCanvasSelection } from '@/maps/map/presentation/composables/useCanvasSelection'
import { useSlideEditing } from '@/maps/map/presentation/composables/useSlideEditing'
import { createElement } from '@/maps/map/presentation/elements'
import type { Box } from '@/maps/map/presentation/geometry'
import type { PresentationElement, PresentationView, ShapeElement } from '@/maps/types/api'

import { newMapView } from '../../../support/fixtures'

function data(x: number, y: number, w = 100, h = 100): PresentationElement {
  return Object.assign(createElement('data', x, y), { w, h })
}

function line(): ShapeElement {
  const el = createElement('line', 0, 0)
  if (el.kind !== 'shape') {
    throw new Error('expected shape element')
  }
  return el
}

/**
 * The editing composable on a bare document: the real selection, a plain
 * element list and a history stub whose version moves exactly as the document's
 * does -- ``snapshot`` records a step, an undo moves the stack on its own.
 */
function setup(initial: PresentationElement[]) {
  const view = ref<PresentationView>({
    ...(newMapView('presentation') as PresentationView),
    elements: initial
  })
  const elements = computed(() => view.value.elements)
  const byId = (id: string | null | undefined): PresentationElement | undefined =>
    id ? elements.value.find((el) => el.id === id) : undefined

  const selection = useCanvasSelection({
    elements,
    byId,
    topLevelId: (id) => id,
    isGrouped: () => false,
    isLocked: () => false
  })

  const selectionBox = ref<Box | null>(null)
  const historyVersion = ref(0)
  const snapshot = vi.fn(() => {
    historyVersion.value++
  })
  const scheduleSave = vi.fn()
  const setElements = (next: PresentationElement[]): void => {
    view.value = { ...view.value, elements: next }
  }

  const editing = useSlideEditing({
    view,
    elements,
    byId,
    isLocked: () => false,
    nextZ: computed(() => 1),
    selection,
    selectionBox,
    historyVersion,
    mutate: (change) => {
      snapshot()
      change()
      scheduleSave()
    },
    setElements,
    snapshot,
    scheduleSave
  })

  return { editing, selection, selectionBox, elements, historyVersion, snapshot }
}

describe('useSlideEditing.remove', () => {
  it('leaves a connector where it was when its dock target is deleted', () => {
    const a = data(0, 0)
    const b = data(400, 200)
    const link = line()
    link.start_ref = a.id
    link.end_ref = b.id
    const { editing, selection, elements } = setup([a, b, link])

    selection.select(b.id)
    editing.remove()

    expect(elements.value.map((el) => el.id)).toEqual([a.id, link.id])
    expect(link.end_ref).toBeNull()
    // The freed end keeps the centre of the deleted element: (450, 250).
    expect({ x: link.x + link.w, y: link.y + link.h }).toEqual({ x: 450, y: 250 })
  })
})

describe('useSlideEditing.nudge', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('records one history step for repeats inside the coalescing window', () => {
    const el = data(0, 0)
    const { editing, selection, snapshot } = setup([el])
    selection.select(el.id)

    editing.nudge(1, 0)
    vi.advanceTimersByTime(100)
    editing.nudge(1, 0)

    expect(snapshot).toHaveBeenCalledTimes(1)
    expect(el.x).toBe(2)
  })

  it('records a fresh step once the window has passed', () => {
    const el = data(0, 0)
    const { editing, selection, snapshot } = setup([el])
    selection.select(el.id)

    editing.nudge(1, 0)
    vi.advanceTimersByTime(1000)
    editing.nudge(1, 0)

    expect(snapshot).toHaveBeenCalledTimes(2)
  })

  it('records a fresh step when the undo stack moved in between', () => {
    const el = data(0, 0)
    const { editing, selection, snapshot, historyVersion } = setup([el])
    selection.select(el.id)

    editing.nudge(1, 0)
    // An undo inside the window: the step the first nudge recorded is no longer
    // the one on top of the stack, so the next nudge must not join it.
    historyVersion.value++
    vi.advanceTimersByTime(100)
    editing.nudge(1, 0)

    expect(snapshot).toHaveBeenCalledTimes(2)
  })
})

describe('useSlideEditing.align', () => {
  it("carries a group's members along when the group is aligned", () => {
    const a = data(0, 0)
    const b = data(100, 0)
    const solo = data(0, 300)
    const { editing, selection, selectionBox } = setup([a, b, solo])

    selection.setSelection([a.id, b.id])
    selectionBox.value = { x: 0, y: 0, w: 200, h: 100 }
    editing.group()
    const groupId = selection.selectedIds.value[0]!

    selection.setSelection([groupId, solo.id])
    selectionBox.value = { x: 0, y: 0, w: 400, h: 400 }
    editing.align('right')

    // The group's box lands at 400 - 200 = 200, so both members shift by 200.
    expect(a.x).toBe(200)
    expect(b.x).toBe(300)
  })
})

describe('useSlideEditing.distribute', () => {
  it("carries a group's members along when the group is distributed", () => {
    const a = data(200, 0)
    const b = data(300, 0)
    const head = data(0, 0)
    const tail = data(800, 0)
    const { editing, selection, selectionBox } = setup([head, a, b, tail])

    selection.setSelection([a.id, b.id])
    selectionBox.value = { x: 200, y: 0, w: 200, h: 100 }
    editing.group()
    const groupId = selection.selectedIds.value[0]!

    selection.setSelection([head.id, groupId, tail.id])
    editing.distribute('x')

    // Boxes of 100/200/100 across 0..900: two gaps of (900 - 400) / 2 = 250, so
    // the group's box lands at 350 and both members shift by 150.
    expect(a.x).toBe(350)
    expect(b.x).toBe(450)
  })
})
