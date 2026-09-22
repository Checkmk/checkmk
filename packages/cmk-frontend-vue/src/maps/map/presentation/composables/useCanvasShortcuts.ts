/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onBeforeUnmount, onMounted } from 'vue'

interface ShortcutOptions {
  interactive: Ref<boolean>
  /** True while an element's text is being edited inline. */
  editingText: () => boolean
  hasSelection: () => boolean
  /** True while the connect walkthrough is running -- Escape leaves it first. */
  connecting: () => boolean
  actions: {
    undo: () => void
    redo: () => void
    copy: () => void
    paste: () => void
    duplicate: () => void
    remove: () => void
    nudge: (dx: number, dy: number) => void
    endTextEdit: () => void
    leaveConnect: () => void
    clearSelection: () => void
  }
}

/** How far an arrow key moves the selection, plain and with Shift. */
const NUDGE = 1
const NUDGE_FAST = 10

const ARROWS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1]
}

/**
 * True while a form control has focus, so canvas shortcuts don't hijack
 * typing -- Backspace must edit an inspector field, not delete elements.
 */
function isTypingTarget(): boolean {
  const el = document.activeElement as HTMLElement | null
  return (
    !!el &&
    (el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.tagName === 'SELECT' ||
      el.isContentEditable)
  )
}

/** The design-tool keyboard the presentation editor offers on the slide. */
export function useCanvasShortcuts(options: ShortcutOptions) {
  const { interactive, editingText, hasSelection, connecting, actions } = options

  function onKey(e: KeyboardEvent): void {
    if (!interactive.value) {
      return
    }
    // Escape ends inline text editing (the blur commits the text). Checked
    // before the typing guard, which swallows every other key while editing.
    if (e.key === 'Escape' && editingText()) {
      ;(document.activeElement as HTMLElement | null)?.blur()
      actions.endTextEdit()
      return
    }
    if (editingText() || isTypingTarget()) {
      return
    }
    const meta = e.ctrlKey || e.metaKey
    const key = e.key.toLowerCase()
    const arrow = ARROWS[e.key]

    if (meta && key === 'z') {
      e.preventDefault()
      if (e.shiftKey) {
        actions.redo()
      } else {
        actions.undo()
      }
    } else if (meta && key === 'y') {
      e.preventDefault()
      actions.redo()
    } else if (meta && key === 'c') {
      actions.copy()
    } else if (meta && key === 'v') {
      e.preventDefault()
      actions.paste()
    } else if (meta && key === 'd') {
      e.preventDefault()
      actions.duplicate()
    } else if ((e.key === 'Delete' || e.key === 'Backspace') && hasSelection()) {
      e.preventDefault()
      actions.remove()
    } else if (arrow && hasSelection()) {
      e.preventDefault()
      const step = e.shiftKey ? NUDGE_FAST : NUDGE
      actions.nudge(arrow[0] * step, arrow[1] * step)
    } else if (e.key === 'Escape') {
      if (connecting()) {
        actions.leaveConnect()
      } else {
        actions.clearSelection()
      }
    }
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
}
