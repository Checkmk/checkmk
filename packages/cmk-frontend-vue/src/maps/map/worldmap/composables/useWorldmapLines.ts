/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The lines a geo map draws between its objects.
 *
 * The line itself is a Leaflet polyline — it has to follow the projection, and
 * a straight line on screen is not a straight line on the globe. What sits on
 * top of it is a marker each: the two grips, the arrowheads and the label.
 * Leaflet places those, the Vue layer paints them, which is why they are handed
 * out as decorations rather than built as markup here.
 *
 * An endpoint bound to an object follows that object, including while it is
 * being dragged (``followLive``): a line that only snapped into place once the
 * drag ended made it impossible to see what one was connecting.
 */
import L from 'leaflet'
import { type ShallowRef, shallowRef } from 'vue'

import type { MarkerMove } from '@/maps/map/worldmap/composables/useWorldmapMarkers'
import {
  type LatLng,
  bindCandidate,
  geoBearing,
  lineEndLatLng,
  midpoint,
  nudgedHandle,
  objectLatLng
} from '@/maps/map/worldmap/geo'
import type { MapElement } from '@/maps/types/api'
import { DIMMED_OPACITY } from '@/maps/utils/objectFilter'

/** Which end of a line an endpoint is. */
export type LineEndpoint = 1 | 2

interface Painted {
  key: string
  element: HTMLElement
  dimmed: boolean
}

/** The grip on one end of a line, shown while the map is edited. */
export interface HandleDecoration extends Painted {
  /** The line's colour, resolved — decorations are drawn outside CSS. */
  color: string
  /** Whether this end follows an object rather than a fixed coordinate. */
  bound: boolean
}

/** The arrowhead on a directed line's end. */
export interface ArrowDecoration extends Painted {
  color: string
  /** The bearing the line arrives at. */
  degrees: number
}

/** The line's own label, at its midpoint. */
export interface LabelDecoration extends Painted {
  /** The line the label belongs to, whose configuration it is drawn from. */
  lineId: string
  text: string
}

/** Everything the Vue layer paints on top of the lines. */
export interface LineDecorations {
  handles: HandleDecoration[]
  arrows: ArrowDecoration[]
  labels: LabelDecoration[]
}

export interface WorldmapLines {
  decorations: Readonly<ShallowRef<LineDecorations>>
  /** Brings the lines and their decorations in line with the objects. */
  sync: () => void
  /** Live positions of the objects being dragged, so bound ends follow. */
  followLive: (moves: MarkerMove[]) => void
  removeAll: () => void
}

/** A Leaflet marker carrying one Vue-painted decoration. */
interface Decoration {
  marker: L.Marker
  element: HTMLElement
}

interface LineEntry {
  polyline: L.Polyline
  /** Wider polyline under the line, where the operator set a border colour. */
  border: L.Polyline | undefined
  handles: Partial<Record<LineEndpoint, Decoration>>
  arrows: Partial<Record<LineEndpoint, Decoration>>
  label: Decoration | undefined
}

/** How a decoration's marker is sized and anchored, and whether it is grabbed. */
interface DecorationSpec {
  iconSize?: [number, number]
  iconAnchor: [number, number]
  draggable?: boolean
}

/** Footprints matching the decorations' own CSS. */
const HANDLE_SPEC: DecorationSpec = { iconSize: [10, 10], iconAnchor: [5, 5], draggable: true }
const ARROW_SPEC: DecorationSpec = { iconSize: [12, 12], iconAnchor: [6, 6] }
/** The label positions itself from the object's configured offset. */
const LABEL_SPEC: DecorationSpec = { iconAnchor: [0, 0] }

const LINE_WEIGHT = 3
const BORDER_WEIGHT = 5
const DASH_PATTERN = '8 6'

/** Glow on a selected line, so it reads over tiles of any colour. */
const SELECTED_GLOW =
  'drop-shadow(0 0 4px var(--color-corporate-green-50)) drop-shadow(0 0 2px var(--color-corporate-green-50))'

const NO_DECORATIONS: LineDecorations = { handles: [], arrows: [], labels: [] }

export function useWorldmapLines(source: {
  map: () => L.Map | null
  objects: () => MapElement[]
  /** The line's colour, resolved: the operator's own, or its state's. */
  colorOf: (object: MapElement) => string
  editMode: () => boolean
  isSelected: (id: string) => boolean
  /** Whether an object passes the map's search and problems-only filter. */
  matches: (object: MapElement) => boolean
  onClick: (id: string, event: MouseEvent) => void
  onContextMenu: (id: string, event: MouseEvent) => void
  onHover: (id: string, event: MouseEvent) => void
  onHoverLeave: () => void
  onEndpointBind: (id: string, endpoint: LineEndpoint, at: LatLng, boundTo: string | null) => void
}): WorldmapLines {
  const entries = new Map<string, LineEntry>()
  const decorations = shallowRef<LineDecorations>(NO_DECORATIONS)
  /** Where the objects currently being dragged are, keyed by object id. */
  const live = new Map<string, LatLng>()
  /** Object ids that some line's endpoint follows, as of the last sync. */
  const boundRefs = new Set<string>()

  /** Where the object a line end is bound to currently sits. */
  function boundAt(
    objects: Map<string, MapElement>,
    refId: string | null | undefined
  ): LatLng | null {
    if (!refId) {
      return null
    }
    const dragged = live.get(refId)
    if (dragged) {
      return dragged
    }
    const object = objects.get(refId)
    return object ? objectLatLng(object) : null
  }

  function decoration(map: L.Map, at: LatLng, spec: DecorationSpec): Decoration {
    const element = document.createElement('div')
    const draggable = spec.draggable === true
    const marker = L.marker(at, {
      icon: L.divIcon({
        className: '',
        html: element,
        ...(spec.iconSize ? { iconSize: spec.iconSize } : {}),
        iconAnchor: spec.iconAnchor
      }),
      // A decoration is a passive part of the line, except for the grips the
      // operator drags — and Leaflet only builds the drag hook on an
      // interactive marker.
      interactive: draggable,
      draggable,
      keyboard: false
    }).addTo(map)
    return { marker, element }
  }

  /** Keeps a decoration at ``at``, creating or dropping it as needed. */
  function place(
    map: L.Map,
    current: Decoration | undefined,
    wanted: boolean,
    at: LatLng,
    spec: DecorationSpec,
    onCreate?: (created: Decoration) => void
  ): Decoration | undefined {
    if (!wanted) {
      current?.marker.remove()
      return undefined
    }
    if (current) {
      current.marker.setLatLng(at)
      return current
    }
    const created = decoration(map, at, spec)
    onCreate?.(created)
    return created
  }

  function bindPointerEvents(polyline: L.Polyline, id: string): void {
    polyline.on('click', (event: L.LeafletMouseEvent) => {
      L.DomEvent.stopPropagation(event)
      source.onClick(id, event.originalEvent)
    })
    polyline.on('contextmenu', (event: L.LeafletMouseEvent) => {
      L.DomEvent.stopPropagation(event)
      source.onContextMenu(id, event.originalEvent)
    })
    polyline.on('mouseover', (event: L.LeafletMouseEvent) => {
      source.onHover(id, event.originalEvent)
    })
    polyline.on('mouseout', () => source.onHoverLeave())
  }

  /** Dropping a grip binds that end to whatever it landed on, or frees it. */
  function bindEndpointDrag(
    map: L.Map,
    grip: Decoration,
    id: string,
    endpoint: LineEndpoint
  ): void {
    grip.marker.on('dragend', () => {
      const dropped = grip.marker.getLatLng()
      const bound = bindCandidate(map, source.objects(), dropped, id)
      // Snapped onto the object it bound to, so the line meets it exactly.
      source.onEndpointBind(
        id,
        endpoint,
        bound?.at ?? [dropped.lat, dropped.lng],
        bound?.object.id ?? null
      )
    })
  }

  function entryFor(map: L.Map, id: string, at: [LatLng, LatLng]): LineEntry {
    const existing = entries.get(id)
    if (existing) {
      return existing
    }
    const polyline = L.polyline(at, { weight: LINE_WEIGHT }).addTo(map)
    // The action bar anchors on ``data-object-id``: a marker carries it on its
    // own element, a path has to be told.
    polyline.getElement()?.setAttribute('data-object-id', id)
    bindPointerEvents(polyline, id)
    const entry: LineEntry = {
      polyline,
      border: undefined,
      handles: {},
      arrows: {},
      label: undefined
    }
    entries.set(id, entry)
    return entry
  }

  function syncLine(
    map: L.Map,
    objects: Map<string, MapElement>,
    object: MapElement,
    painted: LineDecorations
  ): void {
    const start = objectLatLng(object)
    const end = lineEndLatLng(object)
    if (!start || !end) {
      return
    }
    const from = boundAt(objects, object.start_ref) ?? start
    const to = boundAt(objects, object.end_ref) ?? end
    const color = source.colorOf(object)
    const borderColor = object.line_color_border ?? null
    const style = object.line_style ?? 'plain'
    const dashArray = style === 'dashed' ? DASH_PATTERN : undefined
    const dimmed = !source.matches(object)
    const opacity = dimmed ? DIMMED_OPACITY : 1
    const entry = entryFor(map, object.id, [from, to])

    entry.polyline.setLatLngs([from, to])
    entry.polyline.setStyle({ color, dashArray, opacity })
    if (borderColor && !entry.border) {
      entry.border = L.polyline([from, to], { weight: BORDER_WEIGHT }).addTo(map)
      // The border is added after the line, so the line has to come back on top.
      entry.polyline.bringToFront()
    } else if (!borderColor && entry.border) {
      entry.border.remove()
      entry.border = undefined
    }
    entry.border?.setLatLngs([from, to])
    entry.border?.setStyle({ color: borderColor ?? 'transparent', dashArray, opacity })
    // A selected line needs a glow of its own: markers carry their selection on
    // their own element, a path does not.
    const path = entry.polyline.getElement()
    if (path instanceof SVGElement) {
      path.style.filter = source.isSelected(object.id) ? SELECTED_GLOW : ''
    }

    for (const endpoint of [1, 2] as const) {
      const at = endpoint === 1 ? from : to
      const other = endpoint === 1 ? to : from
      const boundRef = endpoint === 1 ? object.start_ref : object.end_ref
      const arrowed =
        style === 'arrow_both' || style === (endpoint === 1 ? 'arrow_start' : 'arrow_end')
      // A bound grip steps aside along the line, so the object it is bound to
      // stays grabbable.
      const gripAt = boundRef ? nudgedHandle(map, at, other) : at

      const grip = place(
        map,
        entry.handles[endpoint],
        source.editMode(),
        gripAt,
        HANDLE_SPEC,
        (created) => bindEndpointDrag(map, created, object.id, endpoint)
      )
      if (grip) {
        entry.handles[endpoint] = grip
        painted.handles.push({
          key: `${object.id}:handle:${endpoint}`,
          element: grip.element,
          dimmed,
          color,
          bound: !!boundRef
        })
      } else {
        delete entry.handles[endpoint]
      }

      const arrow = place(map, entry.arrows[endpoint], arrowed, at, ARROW_SPEC)
      if (arrow) {
        entry.arrows[endpoint] = arrow
        painted.arrows.push({
          key: `${object.id}:arrow:${endpoint}`,
          element: arrow.element,
          dimmed,
          color,
          degrees: endpoint === 1 ? geoBearing(to, from) : geoBearing(from, to)
        })
      } else {
        delete entry.arrows[endpoint]
      }
    }

    const text = object.label?.show === false ? '' : (object.label?.text ?? '')
    entry.label = place(map, entry.label, !!text, midpoint(from, to), LABEL_SPEC)
    if (entry.label) {
      painted.labels.push({
        key: `${object.id}:label`,
        element: entry.label.element,
        dimmed,
        lineId: object.id,
        text
      })
    }
  }

  function remove(entry: LineEntry): void {
    entry.border?.remove()
    entry.polyline.remove()
    entry.label?.marker.remove()
    for (const endpoint of [1, 2] as const) {
      entry.handles[endpoint]?.marker.remove()
      entry.arrows[endpoint]?.marker.remove()
    }
  }

  function sync(): void {
    const map = source.map()
    if (!map) {
      return
    }
    const all = source.objects()
    const objects = new Map(all.map((object) => [object.id, object]))
    const lines = all.filter((object) => object.type === 'line')
    const painted: LineDecorations = { handles: [], arrows: [], labels: [] }
    boundRefs.clear()
    for (const line of lines) {
      syncLine(map, objects, line, painted)
      for (const ref of [line.start_ref, line.end_ref]) {
        if (ref) {
          boundRefs.add(ref)
        }
      }
    }
    const alive = new Set(lines.map((line) => line.id))
    for (const [id, entry] of entries) {
      if (!alive.has(id)) {
        remove(entry)
        entries.delete(id)
      }
    }
    decorations.value = painted
  }

  function followLive(moves: MarkerMove[]): void {
    if (live.size === 0 && !moves.some(({ id }) => boundRefs.has(id))) {
      return
    }
    live.clear()
    for (const { id, lat, lng } of moves) {
      live.set(id, [lat, lng])
    }
    sync()
  }

  function removeAll(): void {
    for (const entry of entries.values()) {
      remove(entry)
    }
    entries.clear()
    live.clear()
    boundRefs.clear()
    decorations.value = NO_DECORATIONS
  }

  return { decorations, sync, followLive, removeAll }
}
