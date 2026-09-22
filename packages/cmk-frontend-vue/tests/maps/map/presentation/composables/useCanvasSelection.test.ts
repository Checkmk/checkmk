/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useCanvasSelection } from '@/maps/map/presentation/composables/useCanvasSelection'
import { createElement, newElementId } from '@/maps/map/presentation/elements'
import type { GroupElement, PresentationElement, ShapeElement } from '@/maps/types/api'

function rect(x: number, y: number, w = 100, h = 100): PresentationElement {
  return Object.assign(createElement('rect', x, y), { w, h })
}

function line(): ShapeElement {
  const el = createElement('line', 0, 0)
  if (el.kind !== 'shape') {
    throw new Error('unreachable')
  }
  return el
}

function group(children: string[]): GroupElement {
  return {
    kind: 'group',
    id: newElementId('group'),
    x: 0,
    y: 0,
    w: 0,
    h: 0,
    rotation: 0,
    z: 10,
    opacity: 1,
    locked: false,
    hidden: false,
    name: null,
    children
  }
}

function selectionOf(els: PresentationElement[]) {
  const elements = ref(els)
  const byId = (id: string | null | undefined): PresentationElement | undefined =>
    elements.value.find((el) => el.id === id)
  const childToGroup = new Map<string, string>()
  for (const el of elements.value) {
    if (el.kind === 'group') {
      el.children.forEach((c) => childToGroup.set(c, el.id))
    }
  }
  return useCanvasSelection({
    elements,
    byId,
    topLevelId: (id) => childToGroup.get(id) ?? id,
    isGrouped: (id) => childToGroup.has(id),
    isLocked: () => false
  })
}

describe('applyMarquee', () => {
  it('tests a connector against the box its endpoints span, not its own', () => {
    // A docked connector keeps a vestigial 10x10 box in the slide's top-left
    // corner while it is drawn between two far-apart elements.
    const a = rect(400, 400)
    const b = rect(800, 400)
    const link = Object.assign(line(), { x: 0, y: 0, w: 10, h: 10 })
    link.start_ref = a.id
    link.end_ref = b.id
    const selection = selectionOf([a, b, link])

    selection.applyMarquee({ left: 0, top: 0, width: 40, height: 40 }, false)
    expect(selection.selectedIds.value).toEqual([])

    selection.applyMarquee({ left: 380, top: 380, width: 500, height: 150 }, false)
    expect(selection.selectedIds.value).toContain(link.id)
  })

  it('leaves group members to their group', () => {
    const a = rect(0, 0)
    const b = rect(200, 0)
    const g = group([a.id, b.id])
    Object.assign(g, { x: 0, y: 0, w: 300, h: 100 })
    const selection = selectionOf([a, b, g])

    selection.applyMarquee({ left: -10, top: -10, width: 400, height: 200 }, false)
    expect(selection.selectedIds.value).toEqual([g.id])
  })
})

describe('moving', () => {
  it('descends into nested groups so an inner group does not leave its members behind', () => {
    const a = rect(0, 0)
    const b = rect(200, 0)
    const inner = group([a.id, b.id])
    const outer = group([inner.id])
    const selection = selectionOf([a, b, inner, outer])

    selection.select(outer.id)
    expect(new Set(selection.moving())).toEqual(new Set([outer.id, inner.id, a.id, b.id]))
  })

  it('survives a group that lists itself', () => {
    const a = rect(0, 0)
    const g = group([a.id])
    g.children.push(g.id)
    const selection = selectionOf([a, g])

    selection.select(g.id)
    expect(new Set(selection.moving())).toEqual(new Set([g.id, a.id]))
  })
})
