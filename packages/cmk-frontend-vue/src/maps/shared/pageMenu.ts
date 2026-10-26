/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The Checkmk page menu above the map list and the image library.
 *
 * ``maps.py`` renders it (``cmk/maps/gui/_page_menu.py``). Its entries act on
 * state the SPA owns, so they dispatch one DOM event with the action as its
 * detail, the way the monitoring pages' export menu does.
 */
import { type InjectionKey, inject, onBeforeUnmount, onMounted, provide } from 'vue'

const PAGE_MENU_ACTIONS = ['create', 'import', 'upload'] as const

export type PageMenuAction = (typeof PAGE_MENU_ACTIONS)[number]

export const MAPS_PAGE_MENU_EVENT: InjectionKey<string> = Symbol('mapsPageMenuEvent')

export function provideMapsPageMenuEvent(eventName: string): void {
  provide(MAPS_PAGE_MENU_EVENT, eventName)
}

function isPageMenuAction(value: unknown): value is PageMenuAction {
  return PAGE_MENU_ACTIONS.some((action) => action === value)
}

export function onPageMenuAction(handler: (action: PageMenuAction) => void): void {
  const eventName = inject(MAPS_PAGE_MENU_EVENT, null)
  if (eventName === null) {
    return
  }
  const listener = (event: Event): void => {
    const action: unknown = event instanceof CustomEvent ? event.detail : undefined
    if (isPageMenuAction(action)) {
      handler(action)
    }
  }
  onMounted(() => document.addEventListener(eventName, listener))
  onBeforeUnmount(() => document.removeEventListener(eventName, listener))
}

/** Keeps a list setting in the page URL without adding a history entry. */
export function replaceUrlParam(name: string, value: string): void {
  const url = new URL(window.location.href)
  if (value) {
    url.searchParams.set(name, value)
  } else {
    url.searchParams.delete(name)
  }
  window.history.replaceState(window.history.state, '', url)
}
