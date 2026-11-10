/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Kept for the life of the page: a view refresh swaps its graph groups for new ones, and their
// skeletons hold the place of the panels that the refresh removed.
const heights = new Map<string, number>()

/** Remember the content height of the panel under key; a panel that is not rendered reports 0. */
export function rememberPanelHeight(key: string, height: number): void {
  if (height > 0) {
    heights.set(key, height)
  }
}

/** The last content height of a panel under key, if one was on the page. */
export function rememberedPanelHeight(key: string): number | undefined {
  return heights.get(key)
}
