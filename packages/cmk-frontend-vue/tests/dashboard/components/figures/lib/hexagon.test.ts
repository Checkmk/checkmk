/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  hexagonGrid,
  hexagonPath,
  hostIndexAt,
  nestedRings
} from '@/dashboard/components/figures/lib/hexagon'

function radii(counts: number[]): number[] {
  return nestedRings(
    counts.map((count) => ({ count })),
    48
  ).map(({ radius }) => radius)
}

describe('hexagon', () => {
  it('draws a pointy-top hexagon around the origin', () => {
    expect(hexagonPath(2)).toBe('M0,-2L1.732,-1L1.732,1L0,2L-1.732,1L-1.732,-1Z')
  })

  it('draws a hexagon around a given centre', () => {
    expect(hexagonPath(2, { x: 10, y: 20 })).toBe(
      'M10,18L11.732,19L11.732,21L10,22L8.268,21L8.268,19Z'
    )
  })

  it('gives the outermost ring the full radius', () => {
    expect(radii([4, 4])[0]).toBe(48)
  })

  it('sizes an inner ring by the remaining count', () => {
    expect(radii([4, 4])[1]).toBeCloseTo(38.186, 2)
  })

  it('gives a zero-count part a zero radius', () => {
    expect(radii([4, 0, 4])[1]).toBe(0)
  })

  it('gives every part a zero radius for a total of zero', () => {
    expect(radii([0, 0])).toEqual([0, 0])
  })
})

describe('hexagonGrid', () => {
  it('lays out hosts in rows that shift every second row', () => {
    const grid = hexagonGrid(3, 104, 120, { layout: 'hosts', maxBoxWidth: 96 })!

    expect(grid.columns).toBe(2)
    expect(grid.boxWidth).toBe(48)
    expect(grid.radius).toBeCloseTo(24.11, 3)
    expect(grid.centers[0]!.x).toBeCloseTo(28, 3)
    expect(grid.centers[0]!.y).toBeCloseTo(37.713, 3)
    expect(grid.centers[2]!.x).toBeCloseTo(52, 3)
    expect(grid.centers[2]!.y).toBeCloseTo(79.282, 3)
    expect(grid.labelHeight).toBeNull()
  })

  it('lays out no hosts in a box without height', () => {
    expect(hexagonGrid(3, 104, 20, { layout: 'hosts', maxBoxWidth: 96 })).toBeNull()
  })

  it('lays out sites in balanced rows with a label', () => {
    const grid = hexagonGrid(2, 208, 120, { layout: 'sites', maxBoxWidth: 96 })!

    expect(grid.columns).toBe(2)
    expect(grid.radius).toBeCloseTo(26.667, 3)
    expect(grid.labelHeight).toBe(12)
    expect(grid.centers[0]!.x).toBeCloseTo(54, 3)
    expect(grid.centers[1]!.x).toBeCloseTo(154, 3)
    expect(grid.centers.map(({ y }) => y)).toEqual([expect.closeTo(46, 3), expect.closeTo(46, 3)])
  })

  it('lays out no sites in a box narrower than 20 pixels', () => {
    expect(hexagonGrid(1, 27, 120, { layout: 'sites', maxBoxWidth: 96 })).toBeNull()
  })

  it.each([
    ['hosts', NaN, 120],
    ['hosts', 104, NaN],
    ['hosts', Infinity, 120],
    ['hosts', 104, Infinity],
    ['sites', NaN, 120],
    ['sites', 208, NaN],
    ['sites', Infinity, 120],
    ['sites', 208, Infinity]
  ] as const)('lays out no %s in a %d by %d box', (layout, width, height) => {
    expect(hexagonGrid(3, width, height, { layout, maxBoxWidth: 96 })).toBeNull()
  })

  it('finds the host box under a point, also in a shifted row', () => {
    const grid = hexagonGrid(3, 104, 120, { layout: 'hosts', maxBoxWidth: 96 })!

    expect(hostIndexAt(grid, 28, 37.713)).toBe(0)
    expect(hostIndexAt(grid, 75, 37.713)).toBe(1)
    expect(hostIndexAt(grid, 52, 79.282)).toBe(2)
    expect(hostIndexAt(grid, 51, 57)).toBe(0)
  })

  it('finds no host outside the boxes of the grid', () => {
    const grid = hexagonGrid(3, 104, 120, { layout: 'hosts', maxBoxWidth: 96 })!

    expect(hostIndexAt(grid, 100, 79.282)).toBeNull()
    expect(hostIndexAt(grid, 28, 2)).toBeNull()
  })
})
