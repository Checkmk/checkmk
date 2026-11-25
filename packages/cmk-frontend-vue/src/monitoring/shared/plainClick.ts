/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { pressDismissesPopup } from 'cmk-ui-library/lib/popupDismissal'
import { onBeforeUnmount } from 'vue'

/**
 * Marks an element that acts on the clicks in it itself, like a cell with a button or chips, so
 * the row around it leaves them alone. A marker rather than `stopPropagation()`, so the click still
 * reaches the document and closes open popups such as a column filter.
 */
export const OWN_CLICKS_ATTRIBUTE = 'data-own-clicks'

/** Elements that act on a click themselves. */
const OWN_CLICK_TARGETS = [
  `[${OWN_CLICKS_ATTRIBUTE}]`,
  'a',
  'button',
  'input',
  'label',
  'select',
  'textarea',
  '[role="button"]',
  '[role="checkbox"]',
  '[role="link"]',
  '[role="menuitem"]'
].join(', ')

/**
 * How long a click waits for a second one, which would make it a double-click marking text.
 * Browsers do not tell the OS double-click interval; this is its default on Windows and macOS,
 * and above GNOME's 400 ms.
 */
export const DOUBLE_CLICK_MS = 500

/** Whether the click closes a popup, which then is all it does, as with the action menu. */
export function closesPopup(event: MouseEvent): boolean {
  return pressDismissesPopup(event)
}

function hasSelection(): boolean {
  return (window.getSelection()?.toString() ?? '') !== ''
}

/** The element within the listening one that acts on this click itself, if any. */
function ownClickTarget(event: MouseEvent): Element | null {
  const own = event.target instanceof Element ? event.target.closest(OWN_CLICK_TARGETS) : null
  return own === event.currentTarget ? null : own
}

/**
 * Whether a click asks the listening element, e.g. a table row, for its details: a primary click
 * without modifier keys, not handled by an element of its own within, not closing a popup, and not
 * the end of marking text to copy.
 */
export function isPlainClick(event: MouseEvent): boolean {
  return (
    event.button === 0 &&
    !(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) &&
    ownClickTarget(event) === null &&
    !closesPopup(event) &&
    !hasSelection()
  )
}

/**
 * Calls `act` for a plain click, but only once no second click followed, so that a double-click
 * marking a name opens nothing. Any press meanwhile, wherever, drops it, e.g. on a checkbox or in
 * another row. A click without a pointer, e.g. from the keyboard, or an `instant` one on
 * something without text to mark acts at once.
 */
export function useDeferredPlainClick(
  act: (event: MouseEvent) => void
): (event: MouseEvent, instant?: boolean) => void {
  let cancel = (): void => {}
  onBeforeUnmount(() => cancel())
  return (event: MouseEvent, instant = false) => {
    cancel()
    if (event.detail > 1 || !isPlainClick(event)) {
      return
    }
    if (event.detail === 0 || instant) {
      act(event)
      return
    }
    const pending = setTimeout(() => {
      drop()
      if (!hasSelection()) {
        act(event)
      }
    }, DOUBLE_CLICK_MS)
    const drop = (): void => {
      clearTimeout(pending)
      document.removeEventListener('pointerdown', drop, true)
    }
    document.addEventListener('pointerdown', drop, { capture: true, once: true })
    cancel = drop
  }
}
