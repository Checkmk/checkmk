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
  return Math.ceil(cellWidth - contentWidth(label) + textWidth(label))
}

/**
 * The width a header cell needs to show its sort button in full: the label's full text and the
 * button's other items, also those it keeps hidden until the column is sorted by.
 *
 * Whatever the cell spends besides the button's content (paddings, the filter button) is kept as
 * is. Returns null while the cell is not laid out.
 */
export function sortButtonFitWidth(
  cell: HTMLElement,
  button: HTMLElement,
  label: HTMLElement
): number | null {
  const cellWidth = cell.getBoundingClientRect().width
  if (cellWidth === 0) {
    return null
  }
  const items = [...button.children] as HTMLElement[]
  const itemsWidth = items
    .map((item) => (item === label ? textWidth(label) : outerWidth(item)))
    .reduce((sum, width) => sum + width, 0)
  const gaps = pixels(getComputedStyle(button).columnGap) * Math.max(items.length - 1, 0)
  return Math.ceil(cellWidth - contentWidth(button) + itemsWidth + gaps)
}

// All widths come from layout rects: mixing in the whole-pixel clientWidth would let the result
// flip by a pixel between layouts at fractional zoom levels.
function contentWidth(element: HTMLElement): number {
  const style = getComputedStyle(element)
  return (
    element.getBoundingClientRect().width -
    pixels(style.paddingLeft) -
    pixels(style.paddingRight) -
    pixels(style.borderLeftWidth) -
    pixels(style.borderRightWidth)
  )
}

function outerWidth(element: HTMLElement): number {
  const style = getComputedStyle(element)
  return (
    element.getBoundingClientRect().width + pixels(style.marginLeft) + pixels(style.marginRight)
  )
}

/** The natural width of an element's text, which a truncated element does not report. */
function textWidth(element: HTMLElement): number {
  const range = document.createRange()
  range.selectNodeContents(element)
  return range.getBoundingClientRect().width
}

function pixels(value: string): number {
  return parseFloat(value) || 0
}
