/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Delegated click-action dispatcher
 *
 * An enforcing Content Security Policy forbids inline event handlers like
 * `onclick="..."`. Instead, the Python code renders a named click action as
 * data attributes on the clickable element which we consume here.
 *
 * See cmk.gui.htmllib.generator:ClickAction for the server side and for how
 * to add a new click action.
 */
import { call_ajax } from '@/modules/ajax'
import { add_bookmark, update_vue_snapin_contents } from '@/modules/sidebar'

type ClickActionArguments = { [key: string]: string }
type ClickAction = (element: HTMLElement, options: ClickActionArguments) => void

// See cmk.gui.htmllib.generator:KnownClickAction
// The type on the Python side and the available keys in this dictionary MUST MATCH.
const click_actions: { [name: string]: ClickAction } = {
  add_bookmark: () => add_bookmark(),
  switch_master_state: (_element, options) => {
    call_ajax(options.url!, {
      method: 'POST',
      response_handler: update_vue_snapin_contents,
      handler_data: 'snapin_master_control'
    })
  }
}

export function init_click_action_dispatcher() {
  // See cmk.gui.htmllib.generator:ClickAction
  document.addEventListener('click', (event: MouseEvent) => {
    if (!(event.target instanceof Element)) return
    const element = event.target.closest<HTMLElement>('*[data-cmk_on_click]')
    if (!element) return
    const action_name: string = element.dataset.cmk_on_click!
    const click_action = click_actions[action_name]
    if (click_action === undefined) {
      console.error(`Unknown click action: ${action_name}`)
      return
    }
    event.preventDefault()
    let options: ClickActionArguments
    if (element.dataset.cmk_on_click_arguments) {
      options = JSON.parse(element.dataset.cmk_on_click_arguments)
    } else {
      options = {}
    }
    click_action(element, options)
  })
}
