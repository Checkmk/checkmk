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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type ClickActionArguments = { [key: string]: any }
export type ClickAction = (element: HTMLElement, options: ClickActionArguments) => void

const registry: { [name: string]: ClickAction } = {}

export function register_click_actions(actions: { [name: string]: ClickAction }) {
  Object.assign(registry, actions)
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
    const action_name: string = element.dataset.cmk_on_click!
    const click_action = registry[action_name]
    if (click_action === undefined) {
      console.error(`Unknown click action: ${action_name}`)
      return
    }
    event.preventDefault()
    const options: ClickActionArguments = element.dataset.cmk_on_click_arguments
      ? JSON.parse(element.dataset.cmk_on_click_arguments)
      : {}
    click_action(element, options)
  })
}
