/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Resizing a grid by the grip of its frame, which sets how many objects a row
 * holds. Each change of columns is handed out while dragging, so the grid lays
 * its objects out anew under the pointer; the release hands out the last, and
 * a gesture the browser cancels hands back what the grid had.
 */
import { gridColumnsAfterDrag, gridLayout } from '@/maps/map/static/gridMembers'
import type { MapElement } from '@/maps/types/api'

type PerRow = MapElement['grid_per_row']

export interface GridResize {
  /** Starts the gesture on a grid of ``members`` objects; a grid without spacing X has none. */
  begin: (event: PointerEvent, grid: MapElement, members: number) => void
  move: (event: PointerEvent) => boolean
  /** What the release leaves the grid with, or ``null`` when no grid was being resized. */
  end: () => { id: string; perRow: number; changed: boolean } | null
  cancel: () => void
}

export function useGridResize(source: {
  /** The element the gesture's pointer is captured on. */
  surface: () => HTMLElement | null
  /**
   * Screen pixels per map unit along x; read once as a gesture starts, since
   * the grid it lays out anew can rescale the canvas.
   */
  pixelsPerUnit: () => number
  onColumns: (id: string, perRow: PerRow) => void
}): GridResize {
  let gesture: {
    id: string
    pointerId: number
    fromX: number
    pixelsPerUnit: number
    stored: PerRow
    from: number
    offsetX: number
    members: number
    perRow: number
    previewed: boolean
  } | null = null

  function begin(event: PointerEvent, grid: MapElement, members: number): void {
    const surface = source.surface()
    const layout = gridLayout(grid)
    if (!surface || event.button !== 0 || layout.offsetX <= 0) {
      return
    }
    surface.setPointerCapture(event.pointerId)
    // A row set wider than the grid has objects starts from what is drawn.
    const from = Math.min(layout.perRow, members)
    gesture = {
      id: grid.id,
      pointerId: event.pointerId,
      fromX: event.clientX,
      pixelsPerUnit: source.pixelsPerUnit(),
      stored: grid.grid_per_row,
      from,
      offsetX: layout.offsetX,
      members,
      perRow: from,
      previewed: false
    }
  }

  function move(event: PointerEvent): boolean {
    if (!gesture || event.pointerId !== gesture.pointerId) {
      return false
    }
    const dx = (event.clientX - gesture.fromX) / gesture.pixelsPerUnit
    const perRow = gridColumnsAfterDrag(gesture.from, gesture.offsetX, dx, gesture.members)
    if (perRow !== gesture.perRow) {
      gesture.perRow = perRow
      gesture.previewed = true
      source.onColumns(gesture.id, perRow)
    }
    return true
  }

  function end(): { id: string; perRow: number; changed: boolean } | null {
    if (!gesture) {
      return null
    }
    const { id, perRow, from } = gesture
    // Measured against what was drawn: a row set wider than the grid has
    // objects stays set when the grip comes back to where it was taken.
    const changed = perRow !== from
    if (!changed) {
      restore()
    }
    gesture = null
    return { id, perRow, changed }
  }

  function cancel(): void {
    if (gesture) {
      restore()
      gesture = null
    }
  }

  /** Takes back the columns the gesture laid the grid out at. */
  function restore(): void {
    if (gesture?.previewed && gesture.perRow !== gesture.stored) {
      source.onColumns(gesture.id, gesture.stored)
    }
  }

  return { begin, move, end, cancel }
}
