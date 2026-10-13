/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where a geo map's objects sit, and the bits of geometry the renderer needs.
 *
 * An object is on the map only once it has both a latitude and a longitude, so
 * that pair — never one half of it — is what the rest of the geo map passes
 * around. The two projected helpers need the live map, because "16 pixels along
 * the line" and "within grabbing distance" are screen distances, and only the
 * projection can turn those into coordinates.
 */
import L from 'leaflet'

import type { MapElement } from '@/maps/types/api'

/** A point on the map, in the order Leaflet takes it. */
export type LatLng = [number, number]

/** What a geo map is looking at, in the shape its settings store it in. */
export interface WorldmapViewport {
  lat: number
  lng: number
  zoom: number
}

function pair(lat: number | null | undefined, lng: number | null | undefined): LatLng | null {
  return lat === null || lat === undefined || lng === null || lng === undefined ? null : [lat, lng]
}

/** Where an object sits, or ``null`` when it has no place on the map yet. */
export function objectLatLng(object: MapElement): LatLng | null {
  return pair(object.lat, object.lng)
}

/** Where a line's far end sits, or ``null`` when the line has no far end yet. */
export function lineEndLatLng(object: MapElement): LatLng | null {
  return pair(object.lat2, object.lng2)
}

export interface PlacedObject {
  object: MapElement
  at: LatLng
}

function placedObjects(objects: MapElement[]): PlacedObject[] {
  return objects.flatMap((object) => {
    const at = objectLatLng(object)
    return at ? [{ object, at }] : []
  })
}

/**
 * The objects that sit at a single coordinate, with where they sit. A line
 * spans two, so it is not one of them: neither "inside the selection band" nor
 * "the point to fit the viewport to" has a single answer for a line.
 */
export function pointObjects(objects: MapElement[]): PlacedObject[] {
  return placedObjects(objects).filter(({ object }) => object.type !== 'line')
}

/**
 * Compass bearing from one point to another, for pointing an arrowhead along a
 * line. Great-circle rather than flat: a line spanning continents leaves its
 * endpoint at a visibly different angle than a straight screen line suggests.
 */
export function geoBearing(from: LatLng, to: LatLng): number {
  const lat1 = (from[0] * Math.PI) / 180
  const lat2 = (to[0] * Math.PI) / 180
  const deltaLng = ((to[1] - from[1]) * Math.PI) / 180
  const y = Math.sin(deltaLng) * Math.cos(lat2)
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLng)
  return (Math.atan2(y, x) * 180) / Math.PI
}

export function midpoint(from: LatLng, to: LatLng): LatLng {
  return [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2]
}

/** How far a bound endpoint's grip steps aside, in screen pixels. */
const HANDLE_NUDGE = 16

/**
 * A bound endpoint's grip, stepped aside along the line so it clears the marker
 * it is bound to — otherwise the grip covers the marker and neither can be
 * grabbed.
 */
export function nudgedHandle(map: L.Map, at: LatLng, toward: LatLng): LatLng {
  const from = map.latLngToContainerPoint(at)
  const to = map.latLngToContainerPoint(toward)
  const dx = to.x - from.x
  const dy = to.y - from.y
  const length = Math.sqrt(dx * dx + dy * dy)
  if (length < 1) {
    return at
  }
  const step = Math.min(HANDLE_NUDGE, length / 2)
  const nudged = map.containerPointToLatLng(
    L.point(from.x + (dx / length) * step, from.y + (dy / length) * step)
  )
  return [nudged.lat, nudged.lng]
}

/** How close a dropped endpoint has to land to bind, in screen pixels. */
const BIND_DISTANCE = 24

/**
 * The object a dropped line endpoint binds to: the nearest one within grabbing
 * distance on screen, or ``null`` for a free endpoint. Screen distance rather
 * than geographic, because the operator aims with the pointer.
 */
export function bindCandidate(
  map: L.Map,
  objects: MapElement[],
  dropped: L.LatLng,
  lineId: string
): PlacedObject | null {
  const at = map.latLngToContainerPoint(dropped)
  let nearest: PlacedObject | null = null
  let shortest = BIND_DISTANCE
  for (const placed of pointObjects(objects)) {
    if (placed.object.id === lineId) {
      continue
    }
    const distance = at.distanceTo(map.latLngToContainerPoint(placed.at))
    if (distance <= shortest) {
      shortest = distance
      nearest = placed
    }
  }
  return nearest
}
