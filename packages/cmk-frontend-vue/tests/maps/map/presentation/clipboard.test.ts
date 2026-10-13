/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { collectWithChildren, instantiate } from '@/maps/map/presentation/clipboard'
import { createElement, newElementId } from '@/maps/map/presentation/elements'
import type { GroupElement, PresentationElement, ShapeElement } from '@/maps/types/api'

function rect(x = 0, y = 0): PresentationElement {
  return createElement('rect', x, y)
}

function group(children: string[]): GroupElement {
  return {
    id: newElementId('group'),
    kind: 'group',
    x: 0,
    y: 0,
    w: 100,
    h: 100,
    rotation: 0,
    z: 5,
    opacity: 1,
    locked: false,
    hidden: false,
    name: null,
    children
  }
}

function line(): ShapeElement {
  const el = createElement('line', 0, 0)
  if (el.kind !== 'shape') {
    throw new Error('expected shape element')
  }
  return el
}

/** Narrow a copy back to a connector -- the copies come back as the union. */
function connector(el: PresentationElement | undefined): ShapeElement {
  if (el?.kind !== 'shape') {
    throw new Error('expected a copied connector')
  }
  return el
}

function lookup(els: PresentationElement[]) {
  return (id: string | null | undefined) => els.find((el) => el.id === id)
}

describe('collectWithChildren', () => {
  it('takes a group along with everything in it', () => {
    const a = rect()
    const b = rect(10, 10)
    const g = group([a.id, b.id])
    const snapshot = collectWithChildren([g.id], lookup([a, b, g]))
    expect(snapshot.tops).toEqual([g.id])
    expect(snapshot.els.map((el) => el.id).sort()).toEqual([a.id, b.id, g.id].sort())
  })

  it('copies rather than references the elements', () => {
    const a = rect()
    const snapshot = collectWithChildren([a.id], lookup([a]))
    snapshot.els[0]!.x = 999
    expect(a.x).toBe(0)
  })

  it('drops ids that are no longer on the slide', () => {
    const a = rect()
    expect(collectWithChildren([a.id, 'gone'], lookup([a])).tops).toEqual([a.id])
  })
})

describe('instantiate', () => {
  it('gives the copies fresh ids and stacks them on top', () => {
    const a = rect(10, 20)
    const { copies, newTops } = instantiate(collectWithChildren([a.id], lookup([a])), 7)
    expect(copies).toHaveLength(1)
    expect(copies[0]!.id).not.toBe(a.id)
    expect(copies[0]).toMatchObject({ x: 34, y: 44, z: 7 })
    expect(newTops).toEqual([copies[0]!.id])
  })

  it('re-docks a copied connector onto the copies of the elements it links', () => {
    const a = rect()
    const b = rect(300, 0)
    const link = line()
    link.start_ref = a.id
    link.end_ref = b.id
    // The copies follow the snapshot's order, so they pair up with [a, b, link].
    const { copies } = instantiate(
      collectWithChildren([a.id, b.id, link.id], lookup([a, b, link])),
      1
    )

    const copiedLink = connector(copies[2])
    expect(copiedLink.start_ref).toBe(copies[0]!.id)
    expect(copiedLink.end_ref).toBe(copies[1]!.id)
  })

  it('keeps an end docked outside the copied set on the original element', () => {
    const outside = rect()
    const link = line()
    link.end_ref = outside.id
    const { copies } = instantiate(collectWithChildren([link.id], lookup([outside, link])), 1)

    expect(connector(copies[0]).end_ref).toBe(outside.id)
  })

  it('remaps a copied group onto the copies of its own members', () => {
    const a = rect()
    const b = rect(10, 10)
    const g = group([a.id, b.id])
    const { copies } = instantiate(collectWithChildren([g.id], lookup([a, b, g])), 1)
    const copiedGroup = copies.find((el) => el.kind === 'group')
    expect(copiedGroup?.kind).toBe('group')
    const copiedIds = copies.map((el) => el.id)
    for (const child of (copiedGroup as GroupElement).children) {
      expect(copiedIds).toContain(child)
      expect([a.id, b.id]).not.toContain(child)
    }
  })
})
