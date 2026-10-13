/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { onBeforeUnmount, onMounted, watch } from 'vue'
import type { Directive, ShallowRef } from 'vue'

export type InlineEditLeaveReason = 'outside' | 'escape'

export interface UseInlineEditOptions {
  /** Reactive getter telling whether the inline edit is currently open. */
  isOpen: () => boolean
  /**
   * Template ref of the edit's bounding element (e.g. from `useTemplateRef`).
   * Clicks beyond it, and Escape, are what leave the edit.
   */
  paneRef: Readonly<ShallowRef<HTMLElement | null>>
  /**
   * Called when the user leaves the open edit by clicking outside its bounds
   * (`'outside'`) or pressing Escape (`'escape'`).
   *
   * Three spurious triggers are filtered out before this fires: clicks that
   * started inside the edit, Escape presses consumed by an open dropdown, and
   * the trailing bubble of the very click that opened the edit.
   */
  onLeave: (reason: InlineEditLeaveReason) => void
}

export interface InlineEdit {
  /** Directive to bind as `v-click-outside` on the bounding element. */
  vClickOutside: Directive
  /** Handler to pass to `v-click-outside`. */
  onOutsideClick: () => void
  /** Handler for `@keydown.esc.capture`. */
  onEscapeCapture: () => void
  /** Handler for `@keydown.esc`. */
  onEscape: () => void
}

/**
 * Drives the open/close lifecycle of an inline edit that commits on
 * click-outside and on Escape: an element that, while open, should leave edit
 * mode when the user clicks beyond it or presses Escape.
 *
 * It owns only the interaction mechanics (arming, inside-click and dropdown
 * guards) and delegates what "leaving" means to {@link UseInlineEditOptions.onLeave},
 * so callers keep full control over validation, committing and focus handling.
 */
export default function useInlineEdit(options: UseInlineEditOptions): InlineEdit {
  const { paneRef } = options
  const vClickOutside = useClickOutside()

  // The click that opens the editor keeps bubbling after Vue mounts the edit
  // branch. Defer arming the outside-click handler by one task so that tail
  // bubble does not turn into the editor's own first leave attempt.
  let outsideArmed = false
  let armTimer: ReturnType<typeof setTimeout> | null = null
  function clearArmTimer(): void {
    if (armTimer !== null) {
      clearTimeout(armTimer)
      armTimer = null
    }
  }

  watch(
    options.isOpen,
    (open) => {
      if (open) {
        clearArmTimer()
        armTimer = setTimeout(() => {
          outsideArmed = true
          armTimer = null
        }, 0)
      } else {
        outsideArmed = false
        clearArmTimer()
      }
    },
    { immediate: true }
  )

  // Prevent a click that starts inside the editor from counting as outside and
  // leaving edit mode.
  let mousedownInside = false
  function onBodyMousedown(event: MouseEvent): void {
    const target = event.target
    mousedownInside =
      paneRef.value !== null && target instanceof Node && paneRef.value.contains(target)
  }
  onMounted(() => {
    document.addEventListener('mousedown', onBodyMousedown, true)
  })
  onBeforeUnmount(() => {
    document.removeEventListener('mousedown', onBodyMousedown, true)
    clearArmTimer()
  })

  function onOutsideClick(): void {
    if (mousedownInside) {
      mousedownInside = false
      return
    }
    if (!outsideArmed) {
      return
    }
    options.onLeave('outside')
  }

  // Escape should close an open dropdown without leaving the editor.
  let escapeAteDropdown = false
  function onEscapeCapture(): void {
    escapeAteDropdown =
      paneRef.value !== null && paneRef.value.querySelector('[aria-expanded="true"]') !== null
  }
  function onEscape(): void {
    if (escapeAteDropdown) {
      escapeAteDropdown = false
      return
    }
    options.onLeave('escape')
  }

  return { vClickOutside, onOutsideClick, onEscapeCapture, onEscape }
}
