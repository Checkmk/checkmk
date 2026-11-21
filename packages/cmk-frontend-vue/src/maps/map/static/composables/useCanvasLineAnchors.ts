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
import { type Ref, type ShallowRef, computed, nextTick, ref, watch } from 'vue'

import { type IconSizes, objectIconSize } from '@/maps/map/objectIconSize'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { sameValues, stableRecords } from '@/maps/utils/stableRecords'

/** The box a line aims at: centre plus half-extents, in map units. */
interface Footprint {
  x: number
  y: number
  halfX: number
  halfY: number
}

/** A rendered icon's offset from its object's anchor, plus its half-extents. */
type MeasuredBox = Omit<Footprint, 'x' | 'y'> & { offX: number; offY: number }

/** Where a line with a free end aims when the other end is bound. */
const FREE_END_OFFSET = 50

type BoundCoords = { x?: number; y?: number; x2?: number; y2?: number }

export interface CanvasLineAnchors {
  /** The bound endpoints of a line, if it has any. */
  boundCoordsFor: (line: MapElement) => BoundCoords
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

/** The icon an object is drawn with, which a caption may move off the object's position. */
export function objectIcon(root: ParentNode, id: string): HTMLElement | null {
  return root.querySelector<HTMLElement>(`[data-object-id="${CSS.escape(id)}"] [data-object-icon]`)
}

export function useCanvasLineAnchors(source: {
  canvas: Readonly<ShallowRef<HTMLElement | null>>
  config: () => MapConfig
  states: () => Readonly<Record<string, ObjectState>>
  dragPositions: () => Record<string, { x: number; y: number }>
  iconSizes: () => IconSizes
  toMapCoords: (offsetX: number, offsetY: number, rect: DOMRect) => { x: number; y: number }
  scale: () => { sx: number; sy: number }
  /** Re-measure whenever the canvas resizes. */
  displaySize: Ref<{ width: number; height: number }>
  /** The NagVis-compatible renderer, which anchors top-left, not centred. */
  classic: () => boolean
}): CanvasLineAnchors {
  // A new state can move a bound object's icon, such as by a wider caption,
  // or leave it in place, such as with new perf data. Only a moved icon makes
  // the lines aim again, so the canvas is not redrawn on every refresh.
  const lastMeasured = new Map<string, MeasuredBox | null>()
  const iconsMoved = ref(0)
  // The same ids keep the same array: the map's objects are replaced on
  // changes that move no line end.
  const boundIds = computed<string[]>((previous) => {
    const ids = [
      ...new Set(
        source
          .config()
          .objects.flatMap((object) =>
            object.type === 'line' ? [object.start_ref, object.end_ref] : []
          )
          .filter((id): id is string => !!id)
      )
    ]
    return previous && sameValues(previous, ids) ? previous : ids
  })
  watch(
    () => new Map(boundIds.value.map((id) => [id, source.states()[id]] as const)),
    (now, before) => {
      for (const [id, state] of now) {
        if (state !== before.get(id) && moved(id)) {
          iconsMoved.value++
          return
        }
      }
    },
    { flush: 'post' }
  )
  // A changed map can move a bound icon, such as by a new caption, a new icon
  // size or an object added with its line. Compared as text, so a grid
  // replacing its members' objects measures nothing.
  const boundObjects = computed(() => {
    const ids = new Set(boundIds.value)
    return JSON.stringify([
      source.iconSizes(),
      source.config().objects.filter((object) => ids.has(object.id))
    ])
  })
  watch(
    boundObjects,
    () => {
      if (boundIds.value.some((id) => moved(id))) {
        iconsMoved.value++
      }
    },
    { flush: 'post' }
  )

  // An object drawn after the canvas, such as when edit mode or "problems
  // only" shows it, is measured once it is there.
  const unmounted = new Set<string>()
  function measureOnceMounted(id: string): void {
    if (unmounted.size === 0) {
      void nextTick(() => {
        const ids = [...unmounted]
        unmounted.clear()
        if (ids.some((candidate) => measuredBox(candidate))) {
          iconsMoved.value++
        }
      })
    }
    unmounted.add(id)
  }

  function moved(id: string): boolean {
    const before = lastMeasured.get(id) ?? null
    const now = measuredBox(id)
    return before && now ? !sameValues(before, now) : before !== now
  }

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
  function measuredBox(id: string): MeasuredBox | null {
    const canvas = source.canvas.value
    if (!canvas) {
      return null
    }
    const icon = objectIcon(canvas, id)
    const wrapper = icon?.closest<HTMLElement>('[data-object-id]')
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
    // Read so the measurement re-runs on mount, on resize and once a bound
    // icon moved.
    void source.displaySize.value
    void iconsMoved.value
    const measured = measuredBox(id)
    lastMeasured.set(id, measured)
    if (measured) {
      return {
        x: position.x + measured.offX,
        y: position.y + measured.offY,
        halfX: measured.halfX,
        halfY: measured.halfY
      }
    }
    // Nothing rendered yet: fall back to the size the object will render at.
    measureOnceMounted(id)
    const object = source.config().objects.find((candidate) => candidate.id === id)
    if (!object) {
      return null
    }
    const size = objectIconSize(object, source.iconSizes())
    const { sx, sy } = source.scale()
    // A canvas not yet laid out has no size to aim at.
    if (sx === 0 || sy === 0) {
      return null
    }
    return { x: position.x, y: position.y, halfX: size / 2 / sx, halfY: size / 2 / sy }
  }

  // So redrawing the canvas does not redraw every line.
  const stableCoords = stableRecords<MapElement, BoundCoords>()

  function boundCoordsFor(line: MapElement): BoundCoords {
    return stableCoords(line, freshBoundCoords(line))
  }

  function freshBoundCoords(line: MapElement): BoundCoords {
    const start = line.start_ref ? footprintOf(line.start_ref) : null
    const end = line.end_ref ? footprintOf(line.end_ref) : null
    const bent =
      line.mid_x !== null &&
      line.mid_x !== undefined &&
      line.mid_y !== null &&
      line.mid_y !== undefined
    const bound: BoundCoords = {}
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
