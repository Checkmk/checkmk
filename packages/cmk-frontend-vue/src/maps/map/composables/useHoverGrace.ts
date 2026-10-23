/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onUnmounted } from 'vue'

/**
 * Close-grace for hover popups with clickable content (HoverMenu pills):
 * leaving the hovered object schedules the close instead of firing it, so
 * the operator can move the pointer onto the card; entering the card
 * cancels the close, leaving the card re-schedules it (the card may overlap
 * its own object, so card->object->card must not flicker).
 *
 * Programmatic exit paths the grace can't see (context menu, click-to-open,
 * closeMenus) must call cancelClose() themselves so a pending timer can't
 * fire into the freshly changed state.
 */
export function useHoverGrace(close: () => void, delayMs = 200) {
  let timer: number | null = null

  function cancelClose(): void {
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
  }

  function scheduleClose(): void {
    cancelClose()
    timer = window.setTimeout(() => {
      timer = null
      close()
    }, delayMs)
  }

  function closeNow(): void {
    cancelClose()
    close()
  }

  onUnmounted(cancelClose)

  return { scheduleClose, cancelClose, closeNow }
}
