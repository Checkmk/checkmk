/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onBeforeUnmount } from 'vue'

/** Whether each popup that a press or click outside closes is open. */
const popups = new Set<() => boolean>()

/**
 * Registers a popup that a press or click outside closes, like a dropdown list, so that what
 * lies behind can tell such a press from one meant for itself (see `isPopupOpen`).
 */
export function useOpenPopup(isOpen: () => boolean): void {
  popups.add(isOpen)
  onBeforeUnmount(() => popups.delete(isOpen))
}

/** Whether any registered popup is open. */
export function isPopupOpen(): boolean {
  return [...popups].some((isOpen) => isOpen())
}
