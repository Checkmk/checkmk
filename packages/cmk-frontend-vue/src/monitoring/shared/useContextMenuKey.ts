/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/** The Menu key and Shift+F10 open the menu of the focused element or its row (CMK-38372). */
import { type Ref, onBeforeUnmount, onMounted } from 'vue'

import { isTextEntry } from './isTextEntry'

const MENU_TRIGGER_SELECTOR = [
  '[aria-haspopup]:not([aria-haspopup="false"])',
  '[role="combobox"]',
  '.monitoring-filter-dropdown [aria-expanded]'
].join(', ')
const MENU_OWNER_SELECTOR = 'tr, th, [role="row"], [role="columnheader"]'

function isMenuKey(event: KeyboardEvent): boolean {
  return event.key === 'ContextMenu' || (event.key === 'F10' && event.shiftKey)
}

function menuTriggerFor(element: Element): HTMLElement | null {
  if (element instanceof HTMLElement && element.matches(MENU_TRIGGER_SELECTOR)) {
    return element
  }
  return (
    element.closest(MENU_OWNER_SELECTOR)?.querySelector<HTMLElement>(MENU_TRIGGER_SELECTOR) ?? null
  )
}

function openMenu(trigger: HTMLElement): void {
  trigger.focus()
  trigger.dispatchEvent(
    new KeyboardEvent('keydown', {
      key: 'ArrowDown',
      code: 'ArrowDown',
      bubbles: true,
      cancelable: true
    })
  )
}

export function useContextMenuKey(scope: Readonly<Ref<HTMLElement | null>>): void {
  let cancelNextContextMenu = false

  function onKeyDown(event: KeyboardEvent): void {
    const active = document.activeElement
    const trigger =
      isMenuKey(event) && active && !isTextEntry(active) && scope.value?.contains(active)
        ? menuTriggerFor(active)
        : null
    if (trigger) {
      cancelNextContextMenu = true
      event.preventDefault()
      openMenu(trigger)
    }
  }

  function onKeyUp(event: KeyboardEvent): void {
    if (event.key === 'ContextMenu' || event.key === 'F10') {
      // Some platforms only fire `contextmenu` once the key is up.
      setTimeout(() => {
        cancelNextContextMenu = false
      }, 0)
    }
  }

  function onContextMenu(event: Event): void {
    if (cancelNextContextMenu) {
      cancelNextContextMenu = false
      event.preventDefault()
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeyDown, true)
    window.addEventListener('keyup', onKeyUp, true)
    window.addEventListener('contextmenu', onContextMenu, true)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeyDown, true)
    window.removeEventListener('keyup', onKeyUp, true)
    window.removeEventListener('contextmenu', onContextMenu, true)
  })
}
