/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onUnmounted, watch } from 'vue'

function focused(): HTMLElement | null {
  return document.activeElement instanceof HTMLElement ? document.activeElement : null
}

/**
 * Puts the focus back where it was when a dialog opened, once it closes.
 * ``CmkPopup`` turns reka's own return off, and it would only go back to a
 * ``DialogTrigger``, which the maps dialogs do not have.
 */
export function useFocusReturn(open: () => boolean): void {
  // A dialog mounted open finds the focus still where it was.
  let lastFocused: HTMLElement | null = open() ? focused() : null

  function restoreFocus(): void {
    if (lastFocused?.isConnected) {
      lastFocused.focus()
    }
    lastFocused = null
  }

  watch(
    open,
    (isOpen) => {
      if (isOpen) {
        lastFocused = focused()
      } else {
        restoreFocus()
      }
    },
    { flush: 'post' }
  )

  // Only once the dialog is gone: while it stands, its focus trap pulls focus back.
  onUnmounted(restoreFocus)
}
