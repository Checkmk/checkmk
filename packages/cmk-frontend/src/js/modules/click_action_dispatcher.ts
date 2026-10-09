/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Delegated click-action dispatcher
 *
 * An enforcing Content Security Policy forbids inline event handlers like
 * `onclick="..."` and `javascript:` URLs. Instead, the Python code renders a
 * named click action as data attributes on the clickable element which we
 * consume here.
 *
 * See cmk.gui.htmllib.generator:ClickAction for the server side and for how
 * to add a new click action.
 */
import type { KnownClickAction } from 'cmk-shared-typing/typescript/legacy_frontend_hooks'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type ClickActionArguments = { [key: string]: any }
// Return true to continue with the default action of the element, e.g. following a link. The
// event is only available when the action is triggered by a click.
export type ClickAction = (
  element: HTMLElement,
  options: ClickActionArguments,
  event?: MouseEvent
) => void | boolean

// Only the click actions known to the backend can be registered. Each bundle registers the ones it
// implements, e.g. mobile.ts only a few, while click_actions.ts has to implement all of them.
type ClickActionRegistry = Partial<Record<KnownClickAction, ClickAction>>

const registry: ClickActionRegistry = {}

export function register_click_actions(actions: ClickActionRegistry) {
  Object.assign(registry, actions)
}

export function run_click_action(
  name: string,
  element: HTMLElement,
  options: ClickActionArguments,
  event?: MouseEvent
): void | boolean {
  // The name comes from the page, so unknown names are only detected here
  const click_action = registry[name as KnownClickAction]
  if (click_action === undefined) {
    console.error(`Unknown click action: ${name}`)
    return
  }
  return click_action(element, options, event)
}

// Links to "#" only trigger actions. Call this when the bundle is evaluated, before the page has
// any links, so they are never followed, not even before the click actions are initialised.
export function prevent_hash_link_navigation() {
  // Use the capture phase, so that handlers which stop the propagation of the event can not make
  // the browser follow the link.
  document.addEventListener(
    'click',
    (event: MouseEvent) => {
      if (event.target instanceof Element && event.target.closest('a[href="#"]')) {
        event.preventDefault()
      }
    },
    true
  )
}

export function init_click_action_dispatcher() {
  document.addEventListener('click', (event: MouseEvent) => {
    if (!(event.target instanceof Element)) return
    const element = event.target.closest<HTMLElement>('*[data-cmk_on_click]')
    if (!element) return
    // Prevent the default action even if the arguments or the action are broken, otherwise a
    // link with a real href would be followed
    let keep_default = false
    try {
      const options: ClickActionArguments = element.dataset.cmk_on_click_arguments
        ? JSON.parse(element.dataset.cmk_on_click_arguments)
        : {}
      keep_default =
        run_click_action(element.dataset.cmk_on_click!, element, options, event) === true
    } finally {
      if (!keep_default) {
        event.preventDefault()
      }
    }
  })
}
