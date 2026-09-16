/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export const ICON_LIST_ICON_SIZE = 16

export const ICON_LIST_GAP = 2

const ICON_LINK_PADDING = 2

const ICON_LIST_ITEM_WIDTH = ICON_LIST_ICON_SIZE + 2 * ICON_LINK_PADDING

export function iconListWidth(count: number): number {
  return count * ICON_LIST_ITEM_WIDTH + Math.max(count - 1, 0) * ICON_LIST_GAP
}
