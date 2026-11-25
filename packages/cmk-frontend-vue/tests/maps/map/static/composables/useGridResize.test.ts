/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useGridResize } from '@/maps/map/static/composables/useGridResize'
import type { MapElement } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'

const pointer = (x: number): PointerEvent =>
  new PointerEvent('pointermove', { clientX: x, clientY: 0, pointerId: 1 })

function gridResize(pixelsPerUnit = 1) {
  const surface = document.createElement('div')
  surface.setPointerCapture = () => {}
  const columns: MapElement['grid_per_row'][] = []
  const resize = useGridResize({
    surface: () => surface,
    pixelsPerUnit: () => pixelsPerUnit,
    onColumns: (_id, perRow) => columns.push(perRow)
  })
  return { resize, columns }
}

const grid = (o: Partial<MapElement> = {}): MapElement =>
  anObject({ id: 'g', type: 'grid', grid_per_row: 4, grid_offset_x: 50, ...o })

describe('useGridResize', () => {
  it('lays the grid out anew at each column the grip crosses, and saves the last', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid(), 20)
    for (const x of [110, 130, 160, 210, 230]) {
      resize.move(pointer(x))
    }

    expect(columns).toEqual([5, 6, 7])
    expect(resize.end()).toEqual({ id: 'g', perRow: 7, changed: true })
  })

  it('counts the drag in map units on a scaled canvas', () => {
    const { resize } = gridResize(2)

    resize.begin(pointer(100), grid(), 20)
    resize.move(pointer(300))

    expect(resize.end()).toMatchObject({ perRow: 6 })
  })

  it('starts from the columns drawn when a row is set wider than the grid has objects', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid({ grid_per_row: 30 }), 5)
    resize.move(pointer(110))
    resize.move(pointer(50))

    expect(columns).toEqual([4])
  })

  it('saves nothing for a grip let go where it was taken', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid(), 20)
    resize.move(pointer(110))

    expect(columns).toEqual([])
    expect(resize.end()).toMatchObject({ changed: false })
  })

  it('saves nothing for a grip dragged out and back again', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid(), 20)
    resize.move(pointer(200))
    resize.move(pointer(100))

    expect(columns).toEqual([6, 4])
    expect(resize.end()).toMatchObject({ perRow: 4, changed: false })
  })

  it('keeps a row set wider than the grid has objects when the grip is only clicked', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid({ grid_per_row: 30 }), 5)

    expect(resize.end()).toMatchObject({ perRow: 5, changed: false })
    expect(columns).toEqual([])
  })

  it('hands back a row set wider than the grid has objects when dragged out and back', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid({ grid_per_row: 30 }), 5)
    resize.move(pointer(50))
    resize.move(pointer(100))

    expect(resize.end()).toMatchObject({ perRow: 5, changed: false })
    expect(columns).toEqual([4, 5, 30])
  })

  it('hands back a row set wider than the grid has objects when the gesture is cancelled', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid({ grid_per_row: 30 }), 5)
    resize.move(pointer(50))
    resize.move(pointer(100))
    resize.cancel()

    expect(columns).toEqual([4, 5, 30])
  })

  it('hands back what the grid had when the browser cancels the gesture', () => {
    const { resize, columns } = gridResize()

    resize.begin(pointer(100), grid(), 20)
    resize.move(pointer(200))
    resize.cancel()

    expect(columns).toEqual([6, 4])
    expect(resize.end()).toBeNull()
  })

  it('leaves the grip to the primary button', () => {
    const { resize } = gridResize()

    resize.begin(new PointerEvent('pointerdown', { clientX: 100, button: 2 }), grid(), 20)

    expect(resize.move(pointer(300))).toBe(false)
  })

  it('has no gesture for a grid without spacing X', () => {
    const { resize } = gridResize()

    resize.begin(pointer(100), grid({ grid_offset_x: 0 }), 20)

    expect(resize.move(pointer(300))).toBe(false)
    expect(resize.end()).toBeNull()
  })
})
