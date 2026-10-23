/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { PresentationElement, ShapeElement } from '@/maps/types/api'

import { type Box, type SlidePoint, topmostAt } from './geometry'

/** Resolves an element id against the slide, as the document composable does. */
export type ElementById = (id: string | null | undefined) => PresentationElement | undefined

/**
 * Lines and arrows are the slide's connectors: they render in a slide-space
 * overlay rather than inline, so they can run at any angle and dock their ends
 * to other elements.
 */
export function isConnectorShape(el: PresentationElement): el is ShapeElement {
  return el.kind === 'shape' && (el.shape === 'line' || el.shape === 'arrow')
}

/** Centre of the element an endpoint is docked to, or null when it is free. */
export function centerOf(byId: ElementById, id: string | null | undefined): SlidePoint | null {
  const el = byId(id ?? undefined)
  return el ? { x: el.x + el.w / 2, y: el.y + el.h / 2 } : null
}

/**
 * Where a connector actually starts and ends: a free endpoint is one of the
 * box's opposite corners (so an arbitrary-angle line is representable), a
 * docked one follows the referenced element's centre.
 */
export function connectorEndpoints(
  el: ShapeElement,
  byId: ElementById
): { start: SlidePoint; end: SlidePoint } {
  return {
    start: centerOf(byId, el.start_ref) ?? { x: el.x, y: el.y },
    end: centerOf(byId, el.end_ref) ?? { x: el.x + el.w, y: el.y + el.h }
  }
}

/** A connector with at least one end docked cannot be dragged by its body. */
export function isDocked(el: ShapeElement, byId: ElementById): boolean {
  return !!(centerOf(byId, el.start_ref) || centerOf(byId, el.end_ref))
}

/**
 * Topmost element a dragged endpoint would dock to at this point: not the
 * connector itself, not another connector, not a group and not a group member.
 */
export function dockTargetAt(
  elements: PresentationElement[],
  p: SlidePoint,
  excludeId: string,
  isGrouped: (id: string) => boolean
): string | null {
  return (
    topmostAt(
      elements,
      p,
      (el) =>
        el.id !== excludeId && el.kind !== 'group' && !isConnectorShape(el) && !isGrouped(el.id)
    )?.id ?? null
  )
}

/**
 * Undock the connector ends that pointed at removed elements, freezing them
 * where they were. A cleared ref falls back to the connector's own box, which
 * is vestigial while docked -- without baking the endpoints in first, deleting
 * a hub element would collapse every line into a stub in the slide's corner.
 * Runs on the survivors while the removed elements still resolve.
 */
export function undockFrom(
  elements: readonly PresentationElement[],
  removed: ReadonlySet<string>,
  byId: ElementById
): void {
  for (const el of elements) {
    if (!isConnectorShape(el)) {
      continue
    }
    const startGone = !!el.start_ref && removed.has(el.start_ref)
    const endGone = !!el.end_ref && removed.has(el.end_ref)
    if (!startGone && !endGone) {
      continue
    }
    const { start, end } = connectorEndpoints(el, byId)
    el.x = start.x
    el.y = start.y
    el.w = end.x - start.x
    el.h = end.y - start.y
    if (startGone) {
      el.start_ref = null
    }
    if (endGone) {
      el.end_ref = null
    }
  }
}

/**
 * The on-slide bounds of an element -- what a badge, a popover or a selection
 * outline anchors on. It lives here because connectors are the whole reason it
 * cannot just be ``el.x/y/w/h``: their own box is vestigial, so they report the
 * box their endpoints span.
 */
export function elementBounds(el: PresentationElement, byId: ElementById): Box {
  if (!isConnectorShape(el)) {
    return { x: el.x, y: el.y, w: el.w, h: el.h }
  }
  const { start, end } = connectorEndpoints(el, byId)
  return {
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    w: Math.abs(end.x - start.x),
    h: Math.abs(end.y - start.y)
  }
}

/** The box the whole selection spans, or null when nothing is selected. */
export function selectionBounds(
  els: readonly PresentationElement[],
  byId: ElementById
): Box | null {
  if (!els.length) {
    return null
  }
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const el of els) {
    const b = elementBounds(el, byId)
    minX = Math.min(minX, b.x)
    minY = Math.min(minY, b.y)
    maxX = Math.max(maxX, b.x + b.w)
    maxY = Math.max(maxY, b.y + b.h)
  }
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY }
}
