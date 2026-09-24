/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { hexagonPath, nestedRings } from '@/dashboard/components/figures/lib/hexagon'

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
