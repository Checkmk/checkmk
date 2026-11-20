/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onScopeDispose } from 'vue'

/** Longer than the gap between two scroll or wheel events of one gesture. */
const SETTLE_MS = 200

/** What a renderer reports about its view; see {@link useMapMotion}. */
export interface MapMotion {
  /** The view started to move, and moves until {@link MapMotion.settled}. */
  started: () => void
  settled: () => void
  /** The view changed, from a source that reports no end: it counts as moving
   *  until it has not changed for a moment. */
  moved: () => void
}

/**
 * Marks ``element`` with ``data-map-moving`` while its map's view moves, by hand
 * or animated, so what is costly to draw on every frame can rest meanwhile.
 *
 * Browsers tick every running animation in every frame they draw, and a pan or
 * zoom draws one frame after another. Only an animation that is not rendered
 * stops costing in all of them; a paused one still does in Firefox.
 */
export function useMapMotion(element: () => HTMLElement | null): MapMotion {
  let settle: ReturnType<typeof setTimeout> | undefined
  let marked: HTMLElement | null = null

  function started(): void {
    clearTimeout(settle)
    if (!marked) {
      marked = element()
      if (marked) {
        marked.dataset['mapMoving'] = ''
      }
    }
  }

  function settled(): void {
    clearTimeout(settle)
    if (marked) {
      delete marked.dataset['mapMoving']
      marked = null
    }
  }

  onScopeDispose(settled)
  return {
    started,
    settled,
    moved: () => {
      started()
      settle = setTimeout(settled, SETTLE_MS)
    }
  }
}
