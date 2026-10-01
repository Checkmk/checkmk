/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * When the treemap opens a tile's hover card, and where: where the pointer
 * comes to rest, staying put while it moves on the tile or crosses others on
 * the way to the card. A card at the tile's edge, or one following the
 * pointer, could not be reached on a large tile.
 */
import { onUnmounted } from 'vue'

import type { Tile } from '../treemapLayout'

/** How long the pointer has to rest on a tile before its card opens. */
export const HOVER_REST_MS = 300

interface TileHoverIntentOptions {
  /** Open the tile's card at a point, closing any other card at once. */
  open: (tile: Tile, x: number, y: number) => void
  /** The pointer left the tile whose card is open: the card may close once
   *  its grace is up, unless the pointer reaches it first. */
  release: () => void
}

const keyOf = (tile: Tile): string => `${tile.data.path}:${tile.data.kind}`

export function useTileHoverIntent(options: TileHoverIntentOptions) {
  let pending: number | null = null
  let current: { key: string; x: number; y: number } | null = null
  let released = false

  function cancelPending(): void {
    if (pending !== null) {
      window.clearTimeout(pending)
      pending = null
    }
  }

  function move(event: MouseEvent, tile: Tile): void {
    const key = keyOf(tile)
    if (current?.key === key) {
      cancelPending()
      // Back on the card's tile before the card closed, or after: either way
      // the card stands where it stood.
      if (released) {
        released = false
        options.open(tile, current.x, current.y)
      }
      return
    }
    const { clientX, clientY } = event
    cancelPending()
    pending = window.setTimeout(() => {
      pending = null
      current = { key, x: clientX, y: clientY }
      released = false
      options.open(tile, clientX, clientY)
    }, HOVER_REST_MS)
  }

  function leave(tile: Tile): void {
    cancelPending()
    if (current?.key === keyOf(tile) && !released) {
      released = true
      options.release()
    }
  }

  /** Forget the open card -- a click changed the tile it belonged to. */
  function reset(): void {
    cancelPending()
    current = null
    released = false
  }

  onUnmounted(cancelPending)

  return { move, leave, reset }
}
