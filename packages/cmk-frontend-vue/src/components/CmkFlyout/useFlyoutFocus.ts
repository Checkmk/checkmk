/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { watch } from 'vue'

export interface FlyoutFocusElements {
  /** The popup element; rendered only while open. */
  popup: () => HTMLElement | null
  /**
   * Restore focus to the control that owns the popup. Called only when the popup closes with focus
   * still inside it; the owner focuses its actual trigger element (the flyout cannot — that control
   * lives in the slot, not on the wrapper the flyout owns).
   */
  restoreFocus: () => void
}

/**
 * Returns focus to the trigger when the popup closes, but only if focus is currently inside the
 * popup — i.e. the user had tabbed or clicked into it. Opening deliberately does NOT move focus:
 * the trigger is typically an editable field (a segmented date/time input), so focus stays put and
 * the user keeps typing while the popup is open.
 */
export function useFlyoutFocus(open: () => boolean, elements: FlyoutFocusElements): void {
  const { popup, restoreFocus } = elements

  watch(open, (isOpen) => {
    if (isOpen) {
      return
    }
    // Pre-flush watcher: this runs before the popup unmounts, so removing the popup never blurs a
    // still-focused element — such a blur would arrive as a focusout with a null relatedTarget,
    // which an enclosing flyout could not tell apart from focus leaving the page.
    const active = document.activeElement
    if (active instanceof HTMLElement && popup()?.contains(active)) {
      restoreFocus()
    }
  })
}
