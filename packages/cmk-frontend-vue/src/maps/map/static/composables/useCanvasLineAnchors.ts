/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where a line bound to an object meets that object.
 *
 * A bound end is drawn on the object's edge, not at its anchor point: a stroke
 * running to the centre disappears under the icon, and an arrowhead ends up
 * buried in it. Which edge depends on where the rest of the line is, so the
 * endpoint is the intersection of the line's direction with the icon's box.
 *
 * The box is measured from the rendered DOM rather than computed, because a
 * caption shifts the icon up inside its stack — the anchor point and the
 * visible icon are not the same place.
 */
import { type Ref, type ShallowRef } from 'vue'

import { objectIconSize } from '@/maps/map/objectIconSize'
import type { MapConfig, MapElement } from '@/maps/types/api'

/** The box a line aims at: centre plus half-extents, in map units. */
interface Footprint {
  x: number
  y: number
  halfX: number
  halfY: number
}

/** Where a line with a free end aims when the other end is bound. */
const FREE_END_OFFSET = 50

export interface CanvasLineAnchors {
  /** The bound endpoints of a line, if it has any. */
  boundCoordsFor: (line: MapElement) => { x?: number; y?: number; x2?: number; y2?: number }
}

/**
 * The point on ``box``'s edge along the ray from its centre toward
 * (``towardX``, ``towardY``) — the side facing the rest of the line.
 */
export function edgePoint(
  box: { x: number; y: number; halfX: number; halfY: number },
  towardX: number,
  towardY: number
): { x: number; y: number } {
  const dx = towardX - box.x
  const dy = towardY - box.y
  if (dx === 0 && dy === 0) {
    return { x: box.x, y: box.y }
  }
  const alongX = dx !== 0 ? box.halfX / Math.abs(dx) : Infinity
  const alongY = dy !== 0 ? box.halfY / Math.abs(dy) : Infinity
  const t = Math.min(alongX, alongY)
  return { x: box.x + dx * t, y: box.y + dy * t }
}

export function useCanvasLineAnchors(source: {
  canvas: Readonly<ShallowRef<HTMLElement | null>>
  config: () => MapConfig
  dragPositions: () => Record<string, { x: number; y: number }>
  iconSizes: () => {
    map: number | null | undefined
    override: number | undefined
    fallback: number
  }
  toMapCoords: (offsetX: number, offsetY: number, rect: DOMRect) => { x: number; y: number }
  scale: () => { sx: number; sy: number }
  /** Re-measure whenever the canvas resizes. */
  displaySize: Ref<{ width: number; height: number }>
  /** The NagVis-compatible renderer, which anchors top-left, not centred. */
  classic: () => boolean
}): CanvasLineAnchors {
  function positionOf(id: string): { x: number; y: number } | null {
    const dragged = source.dragPositions()[id]
    if (dragged) {
      return { x: dragged.x, y: dragged.y }
    }
    const object = source.config().objects.find((candidate) => candidate.id === id)
    return object ? { x: object.x, y: object.y } : null
  }

  /**
   * The rendered icon's offset from its object's anchor, plus its half-extents,
   * read off the DOM. The offset is layout-stable, so a dragged object's lines
   * follow it without a frame of lag.
   */
  function measuredBox(
    id: string
  ): (Omit<Footprint, 'x' | 'y'> & { offX: number; offY: number }) | null {
    const canvas = source.canvas.value
    if (!canvas) {
      return null
    }
    const wrapper = canvas.querySelector<HTMLElement>(`[data-object-id="${CSS.escape(id)}"]`)
    const icon = wrapper?.querySelector<HTMLElement>('[data-object-icon]')
    if (!wrapper || !icon) {
      return null
    }
    const iconRect = icon.getBoundingClientRect()
    if (iconRect.width === 0 || iconRect.height === 0) {
      return null
    }
    const canvasRect = canvas.getBoundingClientRect()
    const wrapperRect = wrapper.getBoundingClientRect()
    const anchorX = source.classic() ? wrapperRect.left : wrapperRect.left + wrapperRect.width / 2
    const anchorY = source.classic() ? wrapperRect.top : wrapperRect.top + wrapperRect.height / 2
    const anchor = source.toMapCoords(
      anchorX - canvasRect.left,
      anchorY - canvasRect.top,
      canvasRect
    )
    const centre = source.toMapCoords(
      iconRect.left + iconRect.width / 2 - canvasRect.left,
      iconRect.top + iconRect.height / 2 - canvasRect.top,
      canvasRect
    )
    const extent = source.toMapCoords(iconRect.width, iconRect.height, canvasRect)
    return {
      offX: centre.x - anchor.x,
      offY: centre.y - anchor.y,
      halfX: extent.x / 2,
      halfY: extent.y / 2
    }
  }

  function footprintOf(id: string): Footprint | null {
    const position = positionOf(id)
    if (!position) {
      return null
    }
    // Read the canvas size so the measurement re-runs on mount and on resize.
    void source.displaySize.value
    const measured = measuredBox(id)
    if (measured) {
      return {
        x: position.x + measured.offX,
        y: position.y + measured.offY,
        halfX: measured.halfX,
        halfY: measured.halfY
      }
    }
    // Nothing rendered yet: fall back to the size the object will render at.
    const object = source.config().objects.find((candidate) => candidate.id === id)
    if (!object) {
      return null
    }
    const size = objectIconSize(object, source.iconSizes())
    const { sx, sy } = source.scale()
    return { x: position.x, y: position.y, halfX: size / 2 / sx, halfY: size / 2 / sy }
  }

  function boundCoordsFor(line: MapElement): {
    x?: number
    y?: number
    x2?: number
    y2?: number
  } {
    const start = line.start_ref ? footprintOf(line.start_ref) : null
    const end = line.end_ref ? footprintOf(line.end_ref) : null
    const bent =
      line.mid_x !== null &&
      line.mid_x !== undefined &&
      line.mid_y !== null &&
      line.mid_y !== undefined
    const bound: { x?: number; y?: number; x2?: number; y2?: number } = {}
    // A bend is what both ends aim at; without one, each end aims at the other
    // end — the opposite object's centre, or its free coordinate.
    if (start) {
      const point = edgePoint(
        start,
        bent ? line.mid_x! : (end?.x ?? line.x2 ?? line.x + FREE_END_OFFSET),
        bent ? line.mid_y! : (end?.y ?? line.y2 ?? line.y + FREE_END_OFFSET)
      )
      bound.x = point.x
      bound.y = point.y
    }
    if (end) {
      const point = edgePoint(
        end,
        bent ? line.mid_x! : (start?.x ?? line.x),
        bent ? line.mid_y! : (start?.y ?? line.y)
      )
      bound.x2 = point.x
      bound.y2 = point.y
    }
    return bound
  }

  return { boundCoordsFor }
}
