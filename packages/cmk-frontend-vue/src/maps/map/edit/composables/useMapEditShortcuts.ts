/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onMounted, onUnmounted } from 'vue'

import type { MapEditor } from '@/maps/map/composables/useMapEditor'

/** Keys that mean "type this", not "act on the selection". */
function isTyping(target: EventTarget | null): boolean {
  const tag = (target as HTMLElement | null)?.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

/** What the keys reach for; the caller owns each of these. */
export interface MapEditShortcutHandlers {
  /**
   * False while something modal sits over the map. A dialog owns the keyboard
   * for as long as it is open — its own Escape closes it, and a key pressed
   * anywhere in it must not reach the object behind it.
   */
  acceptsKeys: () => boolean
  /** Close whatever menu is open. True when one was, so Escape stops there. */
  closeMenus: () => boolean
  /**
   * Delete the selection. The keys hand this back to the caller rather than
   * asking the editor themselves: deleting is confirmed and takes the whole
   * multi-selection, and the keyboard must not be the one path that skips both.
   */
  deleteSelection: () => void
  duplicateSelection: () => void
}

/**
 * The keyboard next to the editing controls: Escape backs out of whatever is
 * open, Delete removes the selection, and Ctrl/Cmd+D duplicates it.
 *
 * Every key does what the toolbar beside the object does, down to when it does
 * nothing — hence the single-object condition on Ctrl/Cmd+D, which is the same
 * one that decides whether the toolbar offers Duplicate at all, and hence
 * ``acceptsKeys``, which mutes them behind an open dialog just as the toolbar
 * is hidden behind one.
 */
export function useMapEditShortcuts(editor: MapEditor, handlers: MapEditShortcutHandlers): void {
  function onKeyDown(event: KeyboardEvent): void {
    if (!editor.editMode.value || !handlers.acceptsKeys() || isTyping(event.target)) {
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      // Escape peels off one layer at a time: first a menu, then the
      // placement in progress, and only then the selection itself.
      if (handlers.closeMenus()) {
        return
      }
      if (editor.placing.value) {
        editor.cancelPlacing()
      } else {
        editor.selectObject(null)
      }
    } else if (
      (event.key === 'Delete' || event.key === 'Backspace') &&
      editor.selectedObjectId.value
    ) {
      event.preventDefault()
      handlers.deleteSelection()
    } else if (
      event.key === 'd' &&
      (event.ctrlKey || event.metaKey) &&
      editor.selectedCount.value === 1
    ) {
      event.preventDefault()
      handlers.duplicateSelection()
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeyDown))
  onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
}
