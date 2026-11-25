/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Whether the press of the current click dismisses a popup, as told by the code that dismisses
 * it: `v-click-outside` and the flyout. Such a click only closes the popup, so what lies behind,
 * like a table row, leaves it alone.
 */
let dismissing = false

// On the window, so it runs ahead of the dismissal code listening on the document.
window.addEventListener(
  'pointerdown',
  () => {
    dismissing = false
  },
  true
)

/** Tells that the current press dismisses a popup. */
export function markPressDismissing(): void {
  dismissing = true
}

/** Whether the click's press dismisses a popup; a click from the keyboard has no press. */
export function pressDismissesPopup(event: MouseEvent): boolean {
  return event.detail > 0 && dismissing
}
