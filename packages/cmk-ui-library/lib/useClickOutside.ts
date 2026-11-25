/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { markPressDismissing } from 'cmk-ui-library/lib/popupDismissal'
import type { Directive } from 'vue'

export interface ClickOutside {
  /** Whether the popup is open, so that a press outside dismisses it (see `popupDismissal`). */
  open: boolean
  /** Called for every click outside the element. */
  close: (event: MouseEvent) => void
}

interface Listeners {
  binding: ClickOutside
  onPointerDown: (event: PointerEvent) => void
  onClick: (event: MouseEvent) => void
}

const listeners = new WeakMap<HTMLElement, Listeners>()

function isOutside(el: HTMLElement, event: Event): boolean {
  return !(event.target instanceof Node && el.contains(event.target))
}

const useClickOutside = (): Directive<HTMLElement, ClickOutside> => ({
  mounted: (el, binding) => {
    const state: Listeners = {
      binding: binding.value,
      onPointerDown: (event) => {
        if (state.binding.open && isOutside(el, event)) {
          markPressDismissing()
        }
      },
      onClick: (event) => {
        if (isOutside(el, event)) {
          state.binding.close(event)
        }
      }
    }
    listeners.set(el, state)
    document.addEventListener('pointerdown', state.onPointerDown, true)
    document.body.addEventListener('click', state.onClick)
  },
  updated: (el, binding) => {
    const state = listeners.get(el)
    if (state) {
      state.binding = binding.value
    }
  },
  unmounted: (el) => {
    const state = listeners.get(el)
    if (state) {
      document.removeEventListener('pointerdown', state.onPointerDown, true)
      document.body.removeEventListener('click', state.onClick)
      listeners.delete(el)
    }
  }
})

export default useClickOutside
