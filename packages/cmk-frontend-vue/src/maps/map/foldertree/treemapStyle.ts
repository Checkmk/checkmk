/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a treemap tile looks like.
 *
 * One visual rule carries the whole map: a container -- a folder, or a host
 * opened to its services -- is a faintly tinted card with a coloured title bar,
 * and a leaf is a solid status chip. So a collapsed folder can never be mistaken
 * for a host, which was the recurring confusion. Everything else follows from
 * the node's state, through the shared monitoring-state tokens.
 */
import type { FolderTreeNode } from '@/maps/types/api'
import { isProblemState } from '@/maps/utils/problemState'
import { stateColorVar } from '@/maps/utils/stateColors'

import type { Tile } from './treemapLayout'

/** Approximate glyph advance at the label's size, used to clip a label to its
 *  tile so a long name ellipsizes instead of bleeding out of the box. */
const CHAR_WIDTH = 7

/** A tile that actually has children drawn inside it. */
export const isExpanded = (tile: Tile): boolean => (tile.children?.length ?? 0) > 0 && !tile.culled

export const isEmptyFolder = (node: FolderTreeNode): boolean =>
  node.kind === 'folder' && node.is_empty

/**
 * A framed card with a title bar, rather than a solid chip: a folder, or a host
 * opened to its services.
 */
export const isContainer = (tile: Tile): boolean =>
  (tile.data.kind === 'folder' && !tile.data.is_empty) ||
  (tile.data.kind === 'host' && isExpanded(tile))

export function tileFill(tile: Tile): string {
  // Containers and chips alike are tinted by their own (worst) state, so a
  // folder's colour matches the list's dot. Containers stay faint via opacity.
  return isEmptyFolder(tile.data) ? 'transparent' : stateColorVar(tile.data.state)
}

export function tileFillOpacity(tile: Tile, light: boolean): number {
  const node = tile.data
  if (isEmptyFolder(node)) {
    return 1
  }
  if (isContainer(tile)) {
    // On a light stage the same low-opacity status colour washes out into a
    // muddy pastel, so the backdrop stays a near-white card and the coloured
    // title bar and frame carry the status instead.
    if (light) {
      return isProblemState(node.state) ? 0.1 : 0.05
    }
    return isProblemState(node.state) ? 0.16 : 0.09
  }
  // Per-site trust: a leaf frozen on its dead site's last known state must not
  // read as a live status, so it sits below even the healthy-chip level.
  if (node.stale) {
    return 0.3
  }
  return isProblemState(node.state) ? 1 : 0.4
}

export function tileStroke(tile: Tile): string {
  if (isEmptyFolder(tile.data)) {
    return 'var(--font-color-dimmed)'
  }
  return isContainer(tile) ? stateColorVar(tile.data.state) : 'var(--default-border-color)'
}

export function tileStrokeWidth(tile: Tile): number {
  if (isEmptyFolder(tile.data)) {
    return 1.4
  }
  return isContainer(tile) && isProblemState(tile.data.state) ? 2 : 1
}

/** The title bar reads the container's worst state, louder for a problem, with
 *  the label's halo keeping it legible on either. */
export function headerFillOpacity(tile: Tile): number {
  return isProblemState(tile.data.state) ? 0.7 : 0.38
}

export function fitLabel(text: string, width: number): string {
  const max = Math.floor((width - 12) / CHAR_WIDTH)
  if (max <= 1) {
    return ''
  }
  if (text.length <= max) {
    return text
  }
  return `${text.slice(0, Math.max(1, max - 1)).trimEnd()}…`
}
