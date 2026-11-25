/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The objects a grid adds, as NagVis lays out a dynmap.
 *
 * The daemon sends one state per host or service the grid's filter matches; the
 * objects are built from those states, so a host that starts or stops matching
 * appears or leaves without a reload. They are placed from the grid's own
 * position, row by row, sorted by name or by state.
 */
import { gridIdOfMember, isGridMemberId } from '@/maps/api/wire'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { GRID_DEFAULTS, newMonitoringElement } from '@/maps/utils/model'

/** The bounds ``map_payload`` sets a grid. */
export const GRID_MEMBER_LIMIT = 1000
export const GRID_OFFSET_MAX = 10000
export const GRID_MAX_PER_MAP = 10

export function mapGrids(map: MapConfig | null | undefined): MapElement[] {
  return map?.view.type === 'static' ? map.objects.filter((o) => o.type === 'grid') : []
}

export function canAddGrid(map: MapConfig | null | undefined): boolean {
  return map?.view.type === 'static' && mapGrids(map).length < GRID_MAX_PER_MAP
}

export interface GridLayout {
  perRow: number
  offsetX: number
  offsetY: number
  sort: 'name' | 'state'
  order: 'asc' | 'desc'
}

// A grid stored through the REST API leaves out what holds its default, and
// the map is read as stored.
export function gridLayout(grid: MapElement): GridLayout {
  return {
    perRow: Math.max(1, grid.grid_per_row ?? GRID_DEFAULTS.grid_per_row),
    offsetX: grid.grid_offset_x ?? GRID_DEFAULTS.grid_offset_x,
    offsetY: grid.grid_offset_y ?? GRID_DEFAULTS.grid_offset_y,
    sort: grid.grid_sort ?? GRID_DEFAULTS.grid_sort,
    order: grid.grid_order ?? GRID_DEFAULTS.grid_order
  }
}

/**
 * How far apart a new grid places its objects: its icons and half an icon
 * between them. NagVis' 30 px suit its smaller icons, not the ones Maps draws.
 */
export function gridSpacingFor(
  iconSize: number
): Pick<MapElement, 'grid_offset_x' | 'grid_offset_y'> {
  const offset = Math.round(iconSize * 1.5)
  return { grid_offset_x: offset, grid_offset_y: offset }
}

/** NagVis' default state weights; ``asc`` puts the heaviest first. */
export function nagvisStateWeight(state: ObjectState): number {
  const handled = state.acknowledged || state.in_downtime
  switch (state.state) {
    case 'DOWN':
      return handled ? 6 : 10
    case 'UNREACHABLE':
      return handled ? 6 : 9
    case 'CRITICAL':
      return handled ? 6 : 8
    case 'WARNING':
      return handled ? 5 : 7
    case 'UNKNOWN':
      return handled ? 3 : 4
    case 'UP':
      return 2
    case 'OK':
      return 1
    default:
      return 0
  }
}

// NagVis compares host and service run together, byte by byte.
function sortName(state: ObjectState): string {
  return `${state.host_name ?? ''}${state.service_description ?? ''}`
}

function byName(a: ObjectState, b: ObjectState): number {
  const left = sortName(a)
  const right = sortName(b)
  return left < right ? -1 : left > right ? 1 : 0
}

export function gridOrder(layout: GridLayout, members: ObjectState[]): ObjectState[] {
  if (layout.sort !== 'state') {
    return [...members].sort(byName)
  }
  const direction = layout.order === 'desc' ? 1 : -1
  return [...members].sort(
    (a, b) => direction * (nagvisStateWeight(a) - nagvisStateWeight(b)) || byName(a, b)
  )
}

export function gridPosition(
  grid: MapElement,
  layout: GridLayout,
  index: number
): { x: number; y: number } {
  return {
    x: grid.x + (index % layout.perRow) * layout.offsetX,
    y: grid.y + Math.floor(index / layout.perRow) * layout.offsetY
  }
}

/**
 * How far a grid reaches from its position: to its last slot, one a pin left
 * empty included, and that slot's icon. ``scale`` turns map coordinates into
 * the canvas' pixels, which the icons keep.
 */
export function gridExtent(
  grid: MapElement,
  members: readonly MapElement[],
  iconSize: number,
  scale: { sx: number; sy: number } = { sx: 1, sy: 1 }
): { width: number; height: number } {
  return {
    width: Math.max(0, ...members.map((member) => member.x - grid.x)) * scale.sx + iconSize,
    height: Math.max(0, ...members.map((member) => member.y - grid.y)) * scale.sy + iconSize
  }
}

// ``grid_id`` alone also matches what was pinned out of the grid.
export function gridMembersOf(objects: readonly MapElement[], gridId: string): MapElement[] {
  return objects.filter((o) => o.grid_id === gridId && isGridMemberId(o.id))
}

/** What an edit of the object changes: a grid member's grid. */
export function editTargetOf(
  objects: readonly MapElement[],
  object: MapElement
): MapElement | null {
  const gridId = gridIdOfMember(object.id)
  return gridId === null ? object : (objects.find((o) => o.id === gridId) ?? null)
}

/** A member as the grid shows it; pinned, it keeps all of this. */
export function gridMemberElement(
  grid: MapElement,
  state: ObjectState,
  position: { x: number; y: number }
): MapElement {
  return {
    ...newMonitoringElement(state.host_name!, state.service_description ?? null),
    id: state.object_id,
    ...position,
    z: grid.z ?? null,
    connection_id: grid.connection_id ?? null,
    label: grid.label,
    label_border: grid.label_border ?? null,
    label_maxlen: grid.label_maxlen ?? null,
    display: grid.display,
    only_hard_states: grid.only_hard_states,
    recognize_services: grid.recognize_services,
    exclude_members: grid.exclude_members ?? null,
    exclude_member_states: grid.exclude_member_states ?? null,
    grid_id: grid.id
  }
}
