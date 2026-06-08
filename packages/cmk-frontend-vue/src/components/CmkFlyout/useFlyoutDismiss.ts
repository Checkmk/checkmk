/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onBeforeUnmount, watch } from 'vue'

export interface FlyoutDismissOptions {
  /** The flyout open state (owned by the parent); the listeners are only attached while open. */
  open: () => boolean
  /** The element wrapping the trigger and the popup; interaction inside it never dismisses. */
  root: () => HTMLElement | null
  /** While a child flyout is open the parent skips its own dismissal (see useFlyoutNesting.ts). */
  hasOpenChild: () => boolean
  /** Close the flyout and revert (the component sets `open = false` and emits `cancel`). */
  onDismiss: () => void
}

/**
 * Dismiss an open flyout when the user leaves it: a document `pointerdown` capture listener
 * (attached while open) handles outside presses, and the returned `onFocusOut` (bound to the root's
 * `focusout`) handles keyboard focus moving out.
 *
 * Outside presses are decided on `pointerdown`, not `click`: the target is still attached (reliable
 * containment even when a select removes the clicked option), and a press that *opens* the flyout
 * runs before the listener attaches, so it can't immediately re-close it.
 */
export function useFlyoutDismiss(options: FlyoutDismissOptions): {
  onFocusOut: (event: FocusEvent) => void
} {
  const { open, root, hasOpenChild, onDismiss } = options

  function onDocumentPointerDown(event: PointerEvent): void {
    const rootEl = root()
    // A press inside the flyout (including its own padding) never dismisses.
    if (rootEl && event.target instanceof Node && rootEl.contains(event.target)) {
      return
    }
    // An open child flyout's own listener (registered later) consumes this press first.
    if (hasOpenChild()) {
      return
    }
    onDismiss()
  }

  function onFocusOut(event: FocusEvent): void {
    // Only an open flyout dismisses on focus leave (a closed trigger's blur is the owner's concern).
    if (!open()) {
      return
    }
    const next = event.relatedTarget
    // Null relatedTarget — focus dropped to nowhere/<body>, the window blurred, or a re-render
    // unmounted the focused node — is never the user leaving, so keep open.
    if (next === null) {
      return
    }
    // Focus stayed inside the flyout: keep open.
    if (next instanceof Node && root()?.contains(next)) {
      return
    }
    onDismiss()
  }

  watch(
    open,
    (isOpen) => {
      if (isOpen) {
        document.addEventListener('pointerdown', onDocumentPointerDown, true)
      } else {
        document.removeEventListener('pointerdown', onDocumentPointerDown, true)
      }
    },
    { immediate: true }
  )
  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onDocumentPointerDown, true)
  })

  return { onFocusOut }
}
