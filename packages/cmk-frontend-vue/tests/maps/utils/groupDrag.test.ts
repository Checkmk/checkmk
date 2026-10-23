/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { MapElement } from '@/maps/types/api'
import { type GroupMember, applyGroupDelta, collectGroupMembers } from '@/maps/utils/groupDrag'

import { anObject } from '../support/fixtures'

function obj(id: string, type: MapElement['type'], x = 0, y = 0): MapElement {
  return anObject({ id, type, x, y, url_target: '' })
}

const project = (o: MapElement): [number, number] | null => [o.x, o.y]

describe('collectGroupMembers', () => {
  const objects = [obj('a', 'image', 1, 1), obj('b', 'image', 2, 2), obj('c', 'image', 3, 3)]

  it('returns nothing when the selection has one or zero members', () => {
    expect(collectGroupMembers(objects, ['a'], 'a', project)).toEqual([])
    expect(collectGroupMembers(objects, [], 'a', project)).toEqual([])
    expect(collectGroupMembers(objects, undefined, 'a', project)).toEqual([])
  })

  it('returns nothing when the grabbed object is not part of the selection', () => {
    expect(collectGroupMembers(objects, ['b', 'c'], 'a', project)).toEqual([])
  })

  it('collects the other selected objects, excluding the grabbed one', () => {
    const members = collectGroupMembers(objects, ['a', 'b', 'c'], 'a', project)
    expect(members).toEqual([
      { id: 'b', init: [2, 2] },
      { id: 'c', init: [3, 3] }
    ])
  })

  it('never includes lines even when selected', () => {
    const withLine = [...objects, obj('l', 'line', 9, 9)]
    const members = collectGroupMembers(withLine, ['a', 'b', 'l'], 'a', project)
    expect(members.map((m) => m.id)).toEqual(['b'])
  })

  it('skips objects whose projection returns null', () => {
    const sparseProject = (o: MapElement): [number, number] | null =>
      o.id === 'b' ? null : [o.x, o.y]
    const members = collectGroupMembers(objects, ['a', 'b', 'c'], 'a', sparseProject)
    expect(members.map((m) => m.id)).toEqual(['c'])
  })
})

describe('applyGroupDelta', () => {
  const members: GroupMember[] = [
    { id: 'b', init: [10, 20] },
    { id: 'c', init: [30, 40] }
  ]

  it('shifts every member by the delta', () => {
    const out = applyGroupDelta(members, [5, -5])
    expect(out.get('b')).toEqual([15, 15])
    expect(out.get('c')).toEqual([35, 35])
  })

  it('clamps both axes to the floor when clampMin is given', () => {
    const out = applyGroupDelta(members, [-100, -100], 0)
    expect(out.get('b')).toEqual([0, 0])
    expect(out.get('c')).toEqual([0, 0])
  })

  it('leaves coordinates unconstrained when clampMin is omitted', () => {
    const out = applyGroupDelta(members, [-100, -100])
    expect(out.get('b')).toEqual([-90, -80])
  })

  it('returns an empty map for no members', () => {
    expect(applyGroupDelta([], [1, 1], 0).size).toBe(0)
  })
})
