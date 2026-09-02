/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Moving objects on a static map.
 *
 * The dragged position is held locally and only handed back on release, so a
 * drag does not put the whole map through the store on every pointer move. The
 * grabbed object's neighbours in a multi-selection move with it by the same
 * delta, and a grid snaps the result.
 *
 * The drag only counts as one once the pointer has travelled a few pixels:
 * below that it is a click, and treating it as a move would make every
 * selection nudge the object.
 */
import { type Reactive, reactive, ref } from 'vue'

import type { MapElement } from '@/maps/types/api'
import { type GroupMember, applyGroupDelta, collectGroupMembers } from '@/maps/utils/groupDrag'

/** Travel, in map units, before a press counts as a drag. */
const DRAG_THRESHOLD = 4

export interface ObjectMove {
  id: string
  x: number
  y: number
}

export interface CanvasObjectDrag {
  /** Live positions of the objects being dragged, keyed by id. */
  positions: Reactive<Record<string, { x: number; y: number }>>
  /** The object under the pointer, or ``null``. */
  draggingId: () => string | null
  /** Whether the current gesture has travelled far enough to be a move. */
  moved: () => boolean
  begin: (event: PointerEvent, object: MapElement) => void
  move: (event: PointerEvent) => boolean
  /** The moves to persist, or ``null`` when nothing was dragged. */
  end: () => ObjectMove[] | null
}

export function useCanvasObjectDrag(source: {
  canvas: () => HTMLElement | null
  objects: () => MapElement[]
  selectedIds: () => string[] | undefined
  toMapCoords: (offsetX: number, offsetY: number, rect: DOMRect) => { x: number; y: number }
  snap: (value: number) => number
  onDragStart: (id: string) => void
}): CanvasObjectDrag {
  const positions = reactive<Record<string, { x: number; y: number }>>({})
  const draggingId = ref<string | null>(null)
  const moved = ref(false)
  let pointerId: number | null = null
  let grabOffsetX = 0
  let grabOffsetY = 0
  let originX = 0
  let originY = 0
  let group: GroupMember[] = []

  function begin(event: PointerEvent, object: MapElement): void {
    const canvas = source.canvas()
    if (!canvas) {
      return
    }
    const rect = canvas.getBoundingClientRect()
    const cursor = source.toMapCoords(event.clientX - rect.left, event.clientY - rect.top, rect)
    grabOffsetX = cursor.x - object.x
    grabOffsetY = cursor.y - object.y
    originX = object.x
    originY = object.y
    moved.value = false
    draggingId.value = object.id
    pointerId = event.pointerId
    positions[object.id] = { x: object.x, y: object.y }
    group = collectGroupMembers(source.objects(), source.selectedIds(), object.id, (object) => [
      object.x,
      object.y
    ])
    for (const member of group) {
      positions[member.id] = { x: member.init[0], y: member.init[1] }
    }
  }

  function move(event: PointerEvent): boolean {
    const id = draggingId.value
    const canvas = source.canvas()
    if (!id || !canvas) {
      return false
    }
    const rect = canvas.getBoundingClientRect()
    const cursor = source.toMapCoords(event.clientX - rect.left, event.clientY - rect.top, rect)
    const x = Math.max(0, source.snap(Math.round(cursor.x - grabOffsetX)))
    const y = Math.max(0, source.snap(Math.round(cursor.y - grabOffsetY)))
    if (
      !moved.value &&
      (Math.abs(x - originX) > DRAG_THRESHOLD || Math.abs(y - originY) > DRAG_THRESHOLD)
    ) {
      moved.value = true
      // Grab the pointer only now: capturing on press would redirect the click
      // of a plain selection away from the object.
      if (pointerId !== null) {
        try {
          canvas.setPointerCapture(pointerId)
        } catch {
          // The pointer may have ended between the press and the first move.
        }
      }
      source.onDragStart(id)
    }
    positions[id] = { x, y }
    if (group.length) {
      const shifted = applyGroupDelta(group, [x - originX, y - originY], 0)
      for (const [memberId, [memberX, memberY]] of shifted) {
        positions[memberId] = { x: memberX, y: memberY }
      }
    }
    return true
  }

  function end(): ObjectMove[] | null {
    const id = draggingId.value
    draggingId.value = null
    pointerId = null
    const members = group
    group = []
    if (!id) {
      return null
    }
    const grabbed = positions[id]
    delete positions[id]
    const moves: ObjectMove[] = [{ id, x: grabbed?.x ?? 0, y: grabbed?.y ?? 0 }]
    for (const member of members) {
      const position = positions[member.id]
      delete positions[member.id]
      if (position) {
        moves.push({ id: member.id, x: position.x, y: position.y })
      }
    }
    return moved.value && grabbed ? moves : null
  }

  return {
    positions,
    draggingId: () => draggingId.value,
    moved: () => moved.value,
    begin,
    move,
    end
  }
}
