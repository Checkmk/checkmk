/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  gridColumnsAfterDrag,
  gridLabelWidths,
  gridLayout,
  gridMemberElement,
  gridOrder,
  gridPosition,
  gridSpacingFor,
  memberLabelWidth
} from '@/maps/map/static/gridMembers'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aMap, aState, anObject } from '../../support/fixtures'

function member(host: string, state = 'UP', extra: Partial<ObjectState> = {}): ObjectState {
  return aState({
    object_id: `auto:grid:g:${host}`,
    type: 'host',
    state,
    host_name: host,
    grid_id: 'g',
    ...extra
  })
}

function grid(overrides: Partial<MapElement> = {}): MapElement {
  return anObject({ id: 'g', type: 'grid', x: 20, y: 700, ...overrides })
}

const hosts = (states: ObjectState[]) => states.map((state) => state.host_name)

describe('gridOrder', () => {
  const byName = gridLayout(grid())
  const byState = gridLayout(grid({ grid_sort: 'state' }))

  it('sorts by name the way NagVis compares bytes, capitals first', () => {
    expect(hosts(gridOrder(byName, [member('b'), member('a'), member('Z')]))).toEqual([
      'Z',
      'a',
      'b'
    ])
  })

  it('puts the worst state first in ascending order', () => {
    const members = [member('ok'), member('down', 'DOWN'), member('unreach', 'UNREACHABLE')]

    expect(hosts(gridOrder(byState, members))).toEqual(['down', 'unreach', 'ok'])
  })

  it('ranks a handled problem below an open warning', () => {
    const members = [
      member('acked', 'DOWN', { acknowledged: true }),
      aState({
        object_id: 'auto:grid:g:web;HTTP',
        type: 'service',
        state: 'WARNING',
        host_name: 'web',
        service_description: 'HTTP'
      })
    ]

    expect(hosts(gridOrder(byState, members))).toEqual(['web', 'acked'])
  })

  it('breaks a tie in state by name', () => {
    expect(hosts(gridOrder(byState, [member('b', 'DOWN'), member('a', 'DOWN')]))).toEqual([
      'a',
      'b'
    ])
  })

  it('puts the best state first in descending order', () => {
    const layout = gridLayout(grid({ grid_sort: 'state', grid_order: 'desc' }))

    expect(hosts(gridOrder(layout, [member('down', 'DOWN'), member('ok')]))).toEqual(['ok', 'down'])
  })

  it('ignores the order when sorting by name', () => {
    const layout = gridLayout(grid({ grid_order: 'desc' }))

    expect(hosts(gridOrder(layout, [member('b'), member('a')]))).toEqual(['a', 'b'])
  })
})

describe('gridPosition', () => {
  it('starts a new row after per_row objects, from the grid', () => {
    const placed = grid({ grid_offset_x: 30, grid_offset_y: 40, grid_per_row: 2 })
    const layout = gridLayout(placed)

    expect([0, 1, 2].map((index) => gridPosition(placed, layout, index))).toEqual([
      { x: 20, y: 700 },
      { x: 50, y: 700 },
      { x: 20, y: 740 }
    ])
  })
})

describe('gridLayout', () => {
  it('takes NagVis defaults for what a stored grid leaves out', () => {
    const stored = { id: 'g', type: 'grid', x: 0, y: 0 } as unknown as MapElement

    expect(gridLayout(stored)).toEqual({
      perRow: 30,
      offsetX: 30,
      offsetY: 30,
      sort: 'name',
      order: 'asc'
    })
  })
})

describe('gridLabelWidths', () => {
  it('gives the labels of a grid the room to the next object in the row', () => {
    const map = aMap({
      objects: [grid({ grid_offset_x: 60 }), anObject({ id: 'h', type: 'host' })]
    })

    expect(gridLabelWidths(map)).toEqual(new Map([['g', 60]]))
  })

  it('leaves the labels of a grid of one column as they are', () => {
    expect(gridLabelWidths(aMap({ objects: [grid({ grid_per_row: 1 })] }))).toEqual(new Map())
  })
})

describe('memberLabelWidth', () => {
  const widths = new Map([['g', 60]])

  it("gives a grid's object its grid's label width", () => {
    expect(memberLabelWidth(widths, anObject({ id: 'auto:grid:g:web01', type: 'host' }))).toBe(60)
  })

  it('gives an object pinned out of the grid none', () => {
    expect(memberLabelWidth(widths, anObject({ id: 'host_1', type: 'host', grid_id: 'g' }))).toBe(
      undefined
    )
  })
})

describe('gridSpacingFor', () => {
  it('leaves half an icon between the icons of a new grid', () => {
    expect(gridSpacingFor(30)).toEqual({ grid_offset_x: 45, grid_offset_y: 45 })
  })
})

describe('gridColumnsAfterDrag', () => {
  it('adds a column for each spacing X the grip is dragged right', () => {
    expect(gridColumnsAfterDrag(4, 50, 100, 20)).toBe(6)
  })

  it('takes the nearer column of a grip dragged between two', () => {
    expect([gridColumnsAfterDrag(4, 50, -24, 20), gridColumnsAfterDrag(4, 50, -26, 20)]).toEqual([
      4, 3
    ])
  })

  it('keeps at least one column', () => {
    expect(gridColumnsAfterDrag(4, 50, -1000, 20)).toBe(1)
  })

  it('stops at one row of all the objects', () => {
    expect(gridColumnsAfterDrag(4, 50, 1000, 20)).toBe(20)
  })
})

describe('gridMemberElement', () => {
  it('stands for the member, looking as the grid says', () => {
    const placed = grid({
      connection_id: 'other',
      label: { show: true, x: 0, y: 0, size: 11, color: '#ffffff', background: 'transparent' },
      label_border: '#000000',
      label_maxlen: 8
    })

    const element = gridMemberElement(placed, member('web'), { x: 5, y: 6 })

    expect(element).toMatchObject({
      id: 'auto:grid:g:web',
      type: 'host',
      host_name: 'web',
      connection_id: 'other',
      grid_id: 'g',
      x: 5,
      y: 6,
      label_border: '#000000',
      label_maxlen: 8
    })
    expect(element.label?.show).toBe(true)
  })
})
