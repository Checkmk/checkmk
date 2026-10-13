/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How large a static map's coordinate space is.
 *
 * Objects are positioned as a fraction of this space, so it has to be stable:
 * derived live, it would grow mid-drag and re-anchor every other object on the
 * map under the moving one. It therefore only ever grows, and only when the map
 * itself changes.
 *
 * A stored size is authoritative — reusing it verbatim is what makes a reload
 * lay the map out exactly as the editor did. It is only ever clamped up, for an
 * object placed beyond it (through the API, say), and then against raw
 * coordinates so the padding below cannot silently re-inflate the stored size.
 *
 * Where the renderer draws the background at its own pixel size, the space is
 * that size and ends no earlier than the last object beyond the image, as NagVis
 * lets the page grow instead of cutting them off. A stored size plays no part
 * there.
 *
 * The NagVis-compatible renderer draws the canvas at exactly this many pixels,
 * so a position stays the same pixel however large the space gets. There it
 * follows every move and resize live, instead of only growing with the map.
 */
import { type Ref, computed, ref, watch } from 'vue'

import { type IconSizes, objectIconSize } from '@/maps/map/objectIconSize'
import type { MapConfig, MapElement } from '@/maps/types/api'

/** Room left to the right of and below an object with no size of its own. */
const OBJECT_PADDING = 150

/** Footprint of a graph object that was never resized. */
const GRAPH_WIDTH = 400
const GRAPH_HEIGHT = 200

/** The space a map with no objects and no stored size still spans. */
const MIN_WIDTH = 800
const MIN_HEIGHT = 600

type Axis = 'x' | 'y'

/** How far an object reaches on ``axis``, a line to its farthest point. */
function reach(object: MapElement, axis: Axis): number {
  return axis === 'x'
    ? Math.max(object.x, object.x2 ?? object.x, object.mid_x ?? object.x)
    : Math.max(object.y, object.y2 ?? object.y, object.mid_y ?? object.y)
}

function edge(object: MapElement, axis: Axis): number {
  if (object.type !== 'graph') {
    return reach(object, axis) + OBJECT_PADDING
  }
  return (
    reach(object, axis) +
    (axis === 'x' ? (object.graph_width ?? GRAPH_WIDTH) : (object.graph_height ?? GRAPH_HEIGHT))
  )
}

/** How far the object's own box extends from its top-left corner. */
function span(object: MapElement, axis: Axis, iconSizes: IconSizes): number {
  switch (object.type) {
    case 'line':
      return 0
    case 'graph':
      return axis === 'x'
        ? (object.graph_width ?? GRAPH_WIDTH)
        : (object.graph_height ?? GRAPH_HEIGHT)
    case 'textbox':
      return (axis === 'x' ? object.textbox_width : object.textbox_height) ?? 0
    default:
      return objectIconSize(object, iconSizes)
  }
}

function extent(
  objects: MapElement[],
  axis: Axis,
  stored: number | null | undefined,
  background: number | undefined,
  iconSizes: IconSizes
): number {
  if (background !== undefined) {
    return objects.reduce(
      (far, object) => Math.max(far, reach(object, axis) + span(object, axis, iconSizes)),
      background
    )
  }
  if (stored !== null && stored !== undefined) {
    return objects.reduce((far, object) => Math.max(far, reach(object, axis)), stored)
  }
  return objects.reduce(
    (far, object) => Math.max(far, edge(object, axis)),
    axis === 'x' ? MIN_WIDTH : MIN_HEIGHT
  )
}

export interface CanvasExtents {
  /** Width of the coordinate space objects are positioned in. */
  width: Readonly<Ref<number>>
  height: Readonly<Ref<number>>
}

export function useCanvasExtents(source: {
  config: () => MapConfig
  /** The background's pixel size, where the renderer draws it at that size. */
  backgroundSize: () => { width: number; height: number } | null
  iconSizes: () => IconSizes
  /** The NagVis-compatible renderer, which draws the space at its pixel size. */
  classic: () => boolean
}): CanvasExtents {
  const derivedWidth = (): number => {
    const config = source.config()
    const background = source.backgroundSize()?.width
    return extent(config.objects, 'x', config.canvas_width, background, source.iconSizes())
  }
  const derivedHeight = (): number => {
    const config = source.config()
    const background = source.backgroundSize()?.height
    return extent(config.objects, 'y', config.canvas_height, background, source.iconSizes())
  }

  const width = ref(MIN_WIDTH)
  const height = ref(MIN_HEIGHT)

  function set(target: Ref<number>, next: number): void {
    if (target.value !== next) {
      target.value = next
    }
  }

  // A different map or background starts over; a new object on the same map
  // only ever widens.
  watch(
    [() => source.config(), () => source.backgroundSize()],
    () => {
      set(width, derivedWidth())
      set(height, derivedHeight())
    },
    { immediate: true }
  )
  watch(
    () => source.config().objects.length,
    () => {
      set(width, Math.max(width.value, derivedWidth()))
      set(height, Math.max(height.value, derivedHeight()))
    }
  )

  return {
    width: computed(() => (source.classic() ? derivedWidth() : width.value)),
    height: computed(() => (source.classic() ? derivedHeight() : height.value))
  }
}
