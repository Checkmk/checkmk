/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * The width a header cell needs to show its label in full.
 *
 * Whatever the cell spends besides the label's text (paddings, the filter button) is kept as is,
 * and the label's text is added at its natural width, which a truncated label does not report.
 * Returns null while the cell is not laid out.
 */
export function headerFitWidth(cell: HTMLElement, label: HTMLElement): number | null {
  const cellWidth = cell.getBoundingClientRect().width
  if (cellWidth === 0) {
    return null
  }
  // All widths come from layout rects: mixing in the whole-pixel clientWidth would let the result
  // flip by a pixel between layouts at fractional zoom levels.
  const style = getComputedStyle(label)
  const labelContentWidth =
    label.getBoundingClientRect().width -
    pixels(style.paddingLeft) -
    pixels(style.paddingRight) -
    pixels(style.borderLeftWidth) -
    pixels(style.borderRightWidth)
  const range = document.createRange()
  range.selectNodeContents(label)
  const textWidth = range.getBoundingClientRect().width
  return Math.ceil(cellWidth - labelContentWidth + textWidth)
}

function pixels(value: string): number {
  return parseFloat(value) || 0
}
