/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KnownClickAction } from 'cmk-shared-typing/typescript/legacy_frontend_hooks'

import { activate_changes } from '@/modules/activation'
import { call_ajax } from '@/modules/ajax'
import { toggle as toggle_inline_help } from '@/modules/help'
import {
  close_active_dropdown,
  close_popup,
  confirmed_form_submit,
  form_submit,
  toggle_popup,
  toggle_suggestions
} from '@/modules/page_menu'
import { toggle_all_rows } from '@/modules/selection'
import { add_bookmark, update_vue_snapin_contents } from '@/modules/sidebar'
import { makeLoadingTransition, querySelectorID } from '@/modules/utils'

import { type ClickAction, register_click_actions } from './click_action_dispatcher'

// Actions of page menu entries close the open dropdown afterwards
function closing_dropdown(action: ClickAction): ClickAction {
  return (element, options, event) => {
    action(element, options, event)
    close_active_dropdown()
  }
}

const click_actions: Record<KnownClickAction, ClickAction> = {
  activate_changes: closing_dropdown((_element, options) =>
    activate_changes(options.mode, options.site_id)
  ),
  add_bookmark: () => add_bookmark(),
  dispatch_custom_event: (_element, options) =>
    document.dispatchEvent(new CustomEvent(options.name)),
  loading_transition: (_element, options, event) => {
    makeLoadingTransition(options.template, 1000, options.title, event)
    return true
  },
  page_menu_close_popup: (element) => close_popup(element),
  page_menu_confirmed_form_submit: closing_dropdown((_element, options) =>
    confirmed_form_submit(options.form_name, options.button_name, options.options)
  ),
  page_menu_form_submit: closing_dropdown((_element, options) =>
    form_submit(options.form_name, options.button_name)
  ),
  page_menu_toggle_popup: (_element, options) => toggle_popup(options.popup_id),
  page_menu_toggle_suggestions: closing_dropdown(() => toggle_suggestions()),
  reload_page: () => location.reload(),
  switch_master_state: (_element, options) => {
    call_ajax(options.url, {
      method: 'POST',
      response_handler: update_vue_snapin_contents,
      handler_data: 'snapin_master_control'
    })
  },
  toggle_all_rows: closing_dropdown(() =>
    toggle_all_rows(querySelectorID('main_page_content') ?? undefined)
  ),
  toggle_inline_help: closing_dropdown(() => toggle_inline_help())
}

register_click_actions(click_actions)
