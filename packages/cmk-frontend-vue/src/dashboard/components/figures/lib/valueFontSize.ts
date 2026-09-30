/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const MIN_FONT_SIZE = 12
const MAX_FONT_SIZE = 50

/** The font size of a large value that fills a box of the given size. */
export function valueFontSize(width: number, height: number): number {
  const fitting = Math.min(width / 5, (height * 2) / 3)
  return Math.min(Math.max(fitting, MIN_FONT_SIZE), MAX_FONT_SIZE)
}
