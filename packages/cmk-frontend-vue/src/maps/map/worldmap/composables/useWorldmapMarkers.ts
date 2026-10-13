/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The Leaflet markers a geo map's objects sit on, and the drag that moves them.
 *
 * Leaflet owns where a marker is — it is the only thing that knows how a
 * coordinate lands on the current viewport — so this keeps the set of markers
 * and their coordinates in line with the objects, and hands each marker's
 * element to the Vue layer to paint the object into. Nothing here decides what
 * an object looks like.
 */
import L from 'leaflet'
import { type ShallowRef, shallowRef } from 'vue'

import { type LatLng, objectLatLng } from '@/maps/map/worldmap/geo'
import type { MapElement } from '@/maps/types/api'
import { type GroupMember, applyGroupDelta, collectGroupMembers } from '@/maps/utils/groupDrag'

/** Where an object was dragged to. */
export interface MarkerMove {
  id: string
  lat: number
  lng: number
}

/** A marker's element, for the Vue layer to render its object into. */
export interface MarkerTarget {
  id: string
  element: HTMLElement
}

export interface WorldmapMarkers {
  targets: Readonly<ShallowRef<MarkerTarget[]>>
  /** Brings the markers in line with the objects: which exist, where they sit,
   *  how they stack, and whether they can be dragged. */
  sync: () => void
  removeAll: () => void
}

interface MarkerEntry {
  marker: L.Marker
  element: HTMLElement
  /** What the marker was last brought in line with, so that a sync that
   *  changes nothing does not walk Leaflet through a reposition anyway. */
  at: LatLng
  stacking: number
  iconBox: string
}

/** Multiplier turning an object's ``z`` into Leaflet's marker stacking offset. */
const Z_STEP = 1000

/** Stacking boost that lifts a search match above everything dimmed. */
const MATCH_BOOST = 10000

export function useWorldmapMarkers(source: {
  map: () => L.Map | null
  objects: () => MapElement[]
  /** Where an object that has no coordinates of its own is shown. */
  fallbackAt: () => LatLng
  /** The object's icon footprint, which is also the marker's hit area. */
  iconSizeOf: (object: MapElement) => number
  defaultZ: () => number
  draggable: () => boolean
  selectedIds: () => string[] | undefined
  /** Whether an object passes the map's search and problems-only filter. */
  matches: (object: MapElement) => boolean
  filterActive: () => boolean
  /** Live positions while a drag is in flight, so bound lines can follow. */
  onDrag: (moves: MarkerMove[]) => void
  onDragEnd: (moves: MarkerMove[]) => void
}): WorldmapMarkers {
  const entries = new Map<string, MarkerEntry>()
  const targets = shallowRef<MarkerTarget[]>([])

  let dragging = false
  /** Where the grabbed marker started, set only when it takes a group along. */
  let dragFrom: L.LatLng | null = null
  let dragGroup: GroupMember[] = []

  /**
   * The objects that get a marker: lines are drawn as polylines, and a host
   * folded into a bundle is represented by the bundle rather than by itself.
   */
  function markerObjects(): MapElement[] {
    const objects = source.objects()
    const bundled = new Set(
      objects.flatMap((object) => (object.bundle_kind ? (object.bundle_hosts ?? []) : []))
    )
    return objects.filter(
      (object) =>
        object.type !== 'line' &&
        !(object.type === 'host' && object.host_name && bundled.has(object.host_name))
    )
  }

  /**
   * A text box is anchored by its top-left corner and sizes itself; everything
   * else is centred on its coordinate, and the icon's footprint is the box
   * Leaflet hit-tests and the operator grabs.
   */
  function iconFor(object: MapElement, element: HTMLElement, size: number): L.DivIcon {
    return object.type === 'textbox'
      ? L.divIcon({ className: '', html: element, iconAnchor: [0, 0] })
      : L.divIcon({
          className: '',
          html: element,
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2]
        })
  }

  /** What ``iconFor`` builds from, so a rebuild only happens when it changes. */
  function iconBoxOf(object: MapElement, size: number): string {
    return `${object.type}|${size}`
  }

  function stackingOf(object: MapElement): number {
    const base = (object.z ?? source.defaultZ()) * Z_STEP
    const boosted = source.filterActive() && source.matches(object)
    return base + (boosted ? MATCH_BOOST : 0)
  }

  /** Where the grabbed marker and everything dragged along with it now sit. */
  function movesFrom(marker: L.Marker, id: string): MarkerMove[] {
    const at = marker.getLatLng()
    const moves: MarkerMove[] = [{ id, lat: at.lat, lng: at.lng }]
    if (dragFrom) {
      for (const [memberId, [lat, lng]] of applyGroupDelta(dragGroup, [
        at.lat - dragFrom.lat,
        at.lng - dragFrom.lng
      ])) {
        moves.push({ id: memberId, lat, lng })
      }
    }
    return moves
  }

  function bindDrag(marker: L.Marker, id: string): void {
    marker.on('dragstart', () => {
      dragging = true
      // A multi-selection moves as one: every other selected object keeps its
      // offset to the one being dragged.
      dragGroup = collectGroupMembers(source.objects(), source.selectedIds(), id, objectLatLng)
      dragFrom = dragGroup.length ? marker.getLatLng() : null
    })
    marker.on('drag', () => {
      const moves = movesFrom(marker, id)
      for (const move of moves.slice(1)) {
        entries.get(move.id)?.marker.setLatLng([move.lat, move.lng])
      }
      source.onDrag(moves)
    })
    marker.on('dragend', () => {
      const moves = movesFrom(marker, id)
      dragging = false
      dragGroup = []
      dragFrom = null
      source.onDragEnd(moves)
    })
  }

  function add(map: L.Map, object: MapElement, at: LatLng, size: number): void {
    const element = document.createElement('div')
    const marker = L.marker(at, {
      icon: iconFor(object, element, size),
      draggable: source.draggable(),
      // The accessible name and the keyboard path live on the Vue content, so
      // Leaflet's own keyboard support would only add a second tab stop.
      keyboard: false,
      zIndexOffset: stackingOf(object)
    })
    entries.set(object.id, {
      marker,
      element,
      at,
      stacking: stackingOf(object),
      iconBox: iconBoxOf(object, size)
    })
    bindDrag(marker, object.id)
    marker.addTo(map)
  }

  function sync(): void {
    const map = source.map()
    if (!map) {
      return
    }
    const objects = markerObjects()
    const present = new Set(objects.map((object) => object.id))
    // A drag moves the grabbed marker and its group itself; writing the stored
    // coordinates back mid-gesture would snap them to where they started.
    const positioning = !dragging
    let structureChanged = false

    for (const object of objects) {
      const at = objectLatLng(object) ?? source.fallbackAt()
      const size = source.iconSizeOf(object)
      const entry = entries.get(object.id)
      if (!entry) {
        add(map, object, at, size)
        structureChanged = true
        continue
      }
      if (positioning && (entry.at[0] !== at[0] || entry.at[1] !== at[1])) {
        entry.at = at
        entry.marker.setLatLng(at)
      }
      const iconBox = iconBoxOf(object, size)
      if (entry.iconBox !== iconBox) {
        entry.iconBox = iconBox
        entry.marker.setIcon(iconFor(object, entry.element, size))
      }
      const stacking = stackingOf(object)
      if (entry.stacking !== stacking) {
        entry.stacking = stacking
        entry.marker.setZIndexOffset(stacking)
      }
      if (source.draggable()) {
        entry.marker.dragging?.enable()
      } else {
        entry.marker.dragging?.disable()
      }
    }

    for (const [id, entry] of entries) {
      if (!present.has(id)) {
        entry.marker.remove()
        entries.delete(id)
        structureChanged = true
      }
    }

    if (structureChanged) {
      targets.value = objects.flatMap((object) => {
        const element = entries.get(object.id)?.element
        return element ? [{ id: object.id, element }] : []
      })
    }
  }

  function removeAll(): void {
    for (const entry of entries.values()) {
      entry.marker.remove()
    }
    entries.clear()
    targets.value = []
  }

  return { targets, sync, removeAll }
}
