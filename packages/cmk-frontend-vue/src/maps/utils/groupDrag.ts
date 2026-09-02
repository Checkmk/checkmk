/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement } from '@/maps/types/api'

export interface GroupMember {
  id: string
  init: [number, number]
}

// Other selected non-line objects that move together with the grabbed one.
// `project` reads each object's drag coordinate (x/y on static canvases, lat/lng
// on geo) and returns null to skip objects that have none.
export function collectGroupMembers(
  objects: MapElement[],
  selectedIds: string[] | undefined,
  grabbedId: string,
  project: (o: MapElement) => [number, number] | null
): GroupMember[] {
  if (!selectedIds || selectedIds.length <= 1 || !selectedIds.includes(grabbedId)) {
    return []
  }
  const members: GroupMember[] = []
  for (const o of objects) {
    if (o.id === grabbedId || o.type === 'line' || !selectedIds.includes(o.id)) {
      continue
    }
    const init = project(o)
    if (init) {
      members.push({ id: o.id, init })
    }
  }
  return members
}

// Shift each member by the grabbed object's delta. `clampMin` floors both axes
// (static keeps objects at >= 0; geo omits it to leave lat/lng unconstrained).
export function applyGroupDelta(
  members: GroupMember[],
  delta: [number, number],
  clampMin?: number
): Map<string, [number, number]> {
  const out = new Map<string, [number, number]>()
  for (const m of members) {
    let a = m.init[0] + delta[0]
    let b = m.init[1] + delta[1]
    if (clampMin !== undefined) {
      a = Math.max(clampMin, a)
      b = Math.max(clampMin, b)
    }
    out.set(m.id, [a, b])
  }
  return out
}
