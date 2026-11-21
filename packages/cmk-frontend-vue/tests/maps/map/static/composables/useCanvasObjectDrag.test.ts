/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useCanvasObjectDrag } from '@/maps/map/static/composables/useCanvasObjectDrag'
import type { MapElement } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'

function dragOn(objects: MapElement[]) {
  const canvas = document.createElement('div')
  return useCanvasObjectDrag({
    canvas: () => canvas,
    objects: () => objects,
    selectedIds: () => undefined,
    toMapCoords: (x, y) => ({ x, y }),
    snap: (value) => value,
    onDragStart: () => {}
  })
}

const pointer = (x: number, y: number) =>
  new PointerEvent('pointermove', { clientX: x, clientY: y, pointerId: 1 })

describe('useCanvasObjectDrag', () => {
  const grid = anObject({ id: 'g', type: 'grid', x: 20, y: 20 })
  const member = anObject({
    id: 'auto:grid:g:web',
    type: 'host',
    host_name: 'web',
    grid_id: 'g',
    x: 50,
    y: 20
  })

  it("moves a dragged grid's members along on screen", () => {
    const drag = dragOn([grid, member])

    drag.begin(pointer(20, 20), grid)
    drag.move(pointer(120, 70))

    expect(drag.positions[member.id]).toEqual({ x: 150, y: 70 })
  })

  it('saves only the grid, not its members, which it lays out again', () => {
    const drag = dragOn([grid, member])
    drag.begin(pointer(20, 20), grid)
    drag.move(pointer(120, 70))

    const moves = drag.end()

    expect(moves).toEqual([{ id: 'g', x: 120, y: 70 }])
    expect(drag.positions[member.id]).toBeUndefined()
  })
})
