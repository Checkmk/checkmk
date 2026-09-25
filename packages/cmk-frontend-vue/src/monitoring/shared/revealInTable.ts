/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

function isSticky(element: Element): boolean {
  return window.getComputedStyle(element).position === 'sticky'
}

function overshoot(start: number, end: number, from: number, to: number): number {
  return start < from ? start - from : end > to ? Math.min(end - to, start - from) : 0
}

/** Like `scrollIntoView` 'nearest', but clear of the sticky header and the pinned columns. */
export function revealInTable(target: HTMLElement, scroller: HTMLElement | null | undefined): void {
  const cell = target.closest<HTMLTableCellElement>('td, th')
  const row = cell?.closest('tr')
  if (!cell || !row || !scroller?.contains(row)) {
    target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    return
  }
  const cells = [...row.cells]
  const index = cells.indexOf(cell)
  const pinnedRights = cells
    .slice(0, index)
    .filter(isSticky)
    .map((pinned) => pinned.getBoundingClientRect().right)
  const pinnedLefts = cells
    .slice(index + 1)
    .filter(isSticky)
    .map((pinned) => pinned.getBoundingClientRect().left)
  const view = scroller.getBoundingClientRect()
  const rect = target.getBoundingClientRect()
  const top = scroller.querySelector('thead')?.getBoundingClientRect().bottom ?? view.top
  scroller.scrollBy({
    top: cell.closest('thead')
      ? 0
      : overshoot(rect.top, rect.bottom, top, view.top + scroller.clientHeight),
    left: isSticky(cell)
      ? 0
      : overshoot(
          rect.left,
          rect.right,
          Math.max(view.left, ...pinnedRights),
          Math.min(view.left + scroller.clientWidth, ...pinnedLefts)
        )
  })
}
