/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where each object sits on a static map, and how the search dims the rest.
 *
 * Objects are placed as a percentage of the coordinate space rather than in
 * pixels: combined with a background stretched to the same box, an object then
 * stays on the same spot of the picture however the canvas is scaled to fit its
 * pane.
 */
import { type ComputedRef, computed } from 'vue'

import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import {
  DIMMED_FILTER,
  DIMMED_OPACITY,
  objectMatchesFilter,
  passesProblemFilter
} from '@/maps/utils/objectFilter'

/** Stacking order of the object under the pointer, above everything placed. */
const DRAGGED_Z = 100
/**
 * Stacking order of a search match: above the objects it has to stand out
 * from, but below the hover card and context menu so it keeps taking clicks
 * while a filter is on.
 */
const MATCH_Z = 49

/** One SVG layer of lines, drawn at a single stacking order. */
export interface LineLayer {
  z: number
  lines: MapElement[]
}

export interface CanvasLayout {
  /** Objects drawn as HTML, in configuration order. */
  placedObjects: ComputedRef<MapElement[]>
  /** Lines grouped so they interleave with the objects by stacking order. */
  lineLayers: ComputedRef<LineLayer[]>
  /** Whether a search or the problems filter is narrowing the map. */
  filtering: ComputedRef<boolean>
  matches: (object: MapElement) => boolean
  objectStyle: (object: MapElement) => Record<string, string | number | undefined>
  lineStyle: (line: MapElement) => Record<string, string | number | undefined>
}

export function useCanvasLayout(source: {
  config: () => MapConfig
  states: () => Record<string, ObjectState>
  width: () => number
  height: () => number
  filterNeedle: () => string | undefined
  problemsOnly: () => boolean | undefined
  editMode: () => boolean
  isAdmin: () => boolean | undefined
  /** The NagVis-compatible renderer, which anchors top-left, not centred. */
  classic: () => boolean
  draggingId: () => string | null
  dragPositions: () => Record<string, { x: number; y: number }>
}): CanvasLayout {
  /**
   * An object with no explicit stacking order takes the map's default — the
   * NagVis-style global — falling back to 1 for maps saved before that existed.
   */
  function resolveZ(object: MapElement): number {
    return object.z ?? source.config().default_z ?? 1
  }

  const placedObjects = computed(() =>
    source.config().objects.filter((object) => object.type !== 'line')
  )

  const lineLayers = computed((): LineLayer[] => {
    const byZ = new Map<number, MapElement[]>()
    for (const object of source.config().objects) {
      if (object.type !== 'line') {
        continue
      }
      const z = resolveZ(object)
      const bucket = byZ.get(z)
      if (bucket) {
        bucket.push(object)
      } else {
        byZ.set(z, [object])
      }
    }
    return [...byZ.entries()].sort(([a], [b]) => a - b).map(([z, lines]) => ({ z, lines }))
  })

  const filtering = computed(
    () => (source.filterNeedle() ?? '').trim() !== '' || !!source.problemsOnly()
  )

  function matches(object: MapElement): boolean {
    return (
      objectMatchesFilter(object, source.filterNeedle() ?? '') &&
      passesProblemFilter(object, source.problemsOnly(), source.states()[object.id]?.state)
    )
  }

  /** Everything filtered out fades rather than vanishing, so the map's shape
   *  stays readable and the operator keeps their bearings. */
  function dimming(object: MapElement): Record<string, string | undefined> {
    const shown = matches(object)
    return {
      opacity: shown ? undefined : String(DIMMED_OPACITY),
      filter: shown ? undefined : DIMMED_FILTER,
      transition: 'opacity 120ms ease, filter 120ms ease'
    }
  }

  function cursorFor(object: MapElement): string {
    if (source.editMode() || source.isAdmin()) {
      return source.draggingId() === object.id ? 'grabbing' : 'grab'
    }
    return source.config().click_action !== 'none' ? 'pointer' : 'default'
  }

  function objectStyle(object: MapElement): Record<string, string | number | undefined> {
    const position = source.dragPositions()[object.id] ?? { x: object.x, y: object.y }
    const width = source.width() || 1
    const height = source.height() || 1
    const z =
      source.draggingId() === object.id
        ? DRAGGED_Z
        : filtering.value && matches(object)
          ? MATCH_Z
          : resolveZ(object)
    return {
      left: `${(position.x / width) * 100}%`,
      top: `${(position.y / height) * 100}%`,
      transform: source.classic() ? 'none' : 'translate(-50%, -50%)',
      cursor: cursorFor(object),
      zIndex: z,
      ...dimming(object)
    }
  }

  function lineStyle(line: MapElement): Record<string, string | number | undefined> {
    // The layer above is click-through so empty areas do not block the objects
    // below; the painted line has to take its own clicks back.
    return { pointerEvents: 'auto', ...dimming(line) }
  }

  return { placedObjects, lineLayers, filtering, matches, objectStyle, lineStyle }
}
