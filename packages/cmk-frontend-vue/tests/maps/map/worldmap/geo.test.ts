/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  geoBearing,
  lineEndLatLng,
  midpoint,
  objectLatLng,
  pointObjects
} from '@/maps/map/worldmap/geo'

import { anObject } from '../../support/fixtures'

describe('objectLatLng', () => {
  it('places an object that has both coordinates', () => {
    expect(objectLatLng(anObject({ id: 'a', type: 'host', lat: 52.5, lng: 13.4 }))).toEqual([
      52.5, 13.4
    ])
  })

  it('leaves an object with only one coordinate unplaced', () => {
    // Half a coordinate is no coordinate: it would put the object on the
    // equator or the prime meridian rather than nowhere.
    expect(objectLatLng(anObject({ id: 'a', type: 'host', lat: 52.5, lng: null }))).toBeNull()
    expect(objectLatLng(anObject({ id: 'a', type: 'host', lat: null, lng: 13.4 }))).toBeNull()
  })

  it('keeps a coordinate of zero, which is a place like any other', () => {
    expect(objectLatLng(anObject({ id: 'a', type: 'host', lat: 0, lng: 0 }))).toEqual([0, 0])
  })
})

describe('lineEndLatLng', () => {
  it("places a line's far end", () => {
    expect(lineEndLatLng(anObject({ id: 'l', type: 'line', lat2: 48.1, lng2: 11.6 }))).toEqual([
      48.1, 11.6
    ])
  })

  it('leaves a line without a far end unplaced', () => {
    expect(lineEndLatLng(anObject({ id: 'l', type: 'line' }))).toBeNull()
  })
})

describe('pointObjects', () => {
  it('keeps only the objects that sit at a coordinate, with where they sit', () => {
    const placed = anObject({ id: 'a', type: 'host', lat: 1, lng: 2 })
    const unplaced = anObject({ id: 'b', type: 'host' })
    expect(pointObjects([placed, unplaced])).toEqual([{ object: placed, at: [1, 2] }])
  })

  it('leaves lines out: a line has two ends, not a place', () => {
    const line = anObject({ id: 'l', type: 'line', lat: 1, lng: 2, lat2: 3, lng2: 4 })
    expect(pointObjects([line])).toEqual([])
  })
})

describe('geoBearing', () => {
  it('points due north when the target is straight up the meridian', () => {
    expect(geoBearing([0, 0], [10, 0])).toBeCloseTo(0)
  })

  it('points due east along the equator', () => {
    expect(geoBearing([0, 0], [0, 10])).toBeCloseTo(90)
  })

  it('follows the great circle, not the straight screen line', () => {
    // Berlin to Tokyo leaves Berlin heading north-east, well away from the
    // due-east a flat map suggests.
    expect(geoBearing([52.52, 13.4], [35.68, 139.77])).toBeCloseTo(41.6, 1)
  })
})

describe('midpoint', () => {
  it('sits halfway between the two ends', () => {
    expect(midpoint([0, 0], [10, 20])).toEqual([5, 10])
  })
})
