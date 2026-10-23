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
 */
import { type Ref, computed, ref, watch } from 'vue'

import type { MapConfig, MapElement } from '@/maps/types/api'

/** Room left to the right of and below an object with no size of its own. */
const OBJECT_PADDING = 150

/** Footprint of a graph object that was never resized. */
const GRAPH_WIDTH = 400
const GRAPH_HEIGHT = 200

/** The space a map with no objects and no stored size still spans. */
const MIN_WIDTH = 800
const MIN_HEIGHT = 600

function rightEdge(object: MapElement): number {
  return object.x + (object.type === 'graph' ? (object.graph_width ?? GRAPH_WIDTH) : OBJECT_PADDING)
}

function bottomEdge(object: MapElement): number {
  return (
    object.y + (object.type === 'graph' ? (object.graph_height ?? GRAPH_HEIGHT) : OBJECT_PADDING)
  )
}

export interface CanvasExtents {
  /** Width of the coordinate space objects are positioned in. */
  width: Ref<number>
  height: Ref<number>
}

export function useCanvasExtents(source: {
  config: () => MapConfig
  /** The background's pixel size, where the renderer sizes the canvas to it. */
  backgroundSize: () => { width: number; height: number } | null
}): CanvasExtents {
  const derivedWidth = (): number => {
    const config = source.config()
    const stored = config.canvas_width
    return stored !== null && stored !== undefined
      ? config.objects.reduce((widest, object) => Math.max(widest, object.x), stored)
      : config.objects.reduce((widest, object) => Math.max(widest, rightEdge(object)), MIN_WIDTH)
  }
  const derivedHeight = (): number => {
    const config = source.config()
    const stored = config.canvas_height
    return stored !== null && stored !== undefined
      ? config.objects.reduce((tallest, object) => Math.max(tallest, object.y), stored)
      : config.objects.reduce(
          (tallest, object) => Math.max(tallest, bottomEdge(object)),
          MIN_HEIGHT
        )
  }

  const derivedW = ref(MIN_WIDTH)
  const derivedH = ref(MIN_HEIGHT)

  function set(target: Ref<number>, next: number): void {
    if (target.value !== next) {
      target.value = next
    }
  }

  // A different map starts over; a new object on the same map only ever widens.
  watch(
    () => source.config(),
    () => {
      set(derivedW, derivedWidth())
      set(derivedH, derivedHeight())
    },
    { immediate: true }
  )
  watch(
    () => source.config().objects.length,
    () => {
      set(derivedW, Math.max(derivedW.value, derivedWidth()))
      set(derivedH, Math.max(derivedH.value, derivedHeight()))
    }
  )

  return {
    width: computed(() => source.backgroundSize()?.width ?? derivedW.value),
    height: computed(() => source.backgroundSize()?.height ?? derivedH.value)
  }
}
