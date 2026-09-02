/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The box a card opens next to, in viewport coordinates.
 *
 * Whoever drew the object took the measurement and passes it along with the
 * event: the canvas owns the node, and a card that went looking for it again
 * would have to assume there is exactly one map on the page.
 */
export interface AnchorRect {
  left: number
  top: number
  right: number
  bottom: number
}

/** The box of the element an event came from, or null where it has no size. */
export function anchorRectOf(target: EventTarget | null): AnchorRect | null {
  const rect = (target as HTMLElement | null)?.getBoundingClientRect()
  if (!rect || (rect.width === 0 && rect.height === 0)) {
    return null
  }
  return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom }
}
