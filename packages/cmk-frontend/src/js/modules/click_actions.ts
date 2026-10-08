/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KnownClickAction } from 'cmk-shared-typing/typescript/legacy_frontend_hooks'

import { activate_changes } from '@/modules/activation'
import { call_ajax } from '@/modules/ajax'
import { waiting_flash_message } from '@/modules/forms'
import { toggle as toggle_inline_help } from '@/modules/help'
import {
  close_active_dropdown,
  close_popup,
  confirmed_form_submit,
  form_submit,
  toggle_popup,
  toggle_suggestions
} from '@/modules/page_menu'
import { add_to_visual, graph_export, pagetype_add_to_container } from '@/modules/popup_menu'
import { toggle_all_rows } from '@/modules/selection'
import { start as start_service_discovery } from '@/modules/service_discovery'
import { add_bookmark, update_vue_snapin_contents } from '@/modules/sidebar'
import { makeLoadingTransition, makeuri, querySelectorID } from '@/modules/utils'

import { type ClickAction, register_click_actions } from './click_action_dispatcher'

// Actions of page menu entries close the open dropdown afterwards
function closing_dropdown(action: ClickAction): ClickAction {
  return (element, options, event) => {
    action(element, options, event)
    close_active_dropdown()
  }
}

function set_toggle_icon(selector: string, on: boolean) {
  document.querySelector(selector)?.querySelector('img')?.classList.toggle('on', on)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const node_instance = () => (window as any).node_instance

const dispatch_custom_event: ClickAction = (_element, options) =>
  document.dispatchEvent(new CustomEvent(options.name, { detail: options.detail }))

const click_actions: Record<KnownClickAction, ClickAction> = {
  activate_changes: closing_dropdown((_element, options) =>
    activate_changes(options.mode, options.site_id)
  ),
  add_bookmark: () => add_bookmark(),
  add_to_visual: closing_dropdown((_element, options) =>
    add_to_visual(options.visual_type, options.visual_name)
  ),
  dispatch_custom_event: dispatch_custom_event,
  graph_export: closing_dropdown((_element, options) => graph_export(options.page)),
  loading_transition: (_element, options, event) => {
    makeLoadingTransition(options.template, 1000, options.title, event)
    return true
  },
  nodevis_toggle_compare_history: closing_dropdown(() => {
    const new_state = node_instance().toggle_compare_history()
    set_toggle_icon('.suggestion.topology_compare_history', new_state)
  }),
  nodevis_toggle_layout_designer: closing_dropdown(() => {
    const new_state = node_instance().toggle_layout_designer()
    set_toggle_icon('.suggestion.topology_layout_designer', new_state)
    set_toggle_icon('#menu_shortcut_edit_layout', new_state)
  }),
  page_menu_close_popup: (element) => close_popup(element),
  page_menu_confirmed_form_submit: closing_dropdown((_element, options) =>
    confirmed_form_submit(options.form_name, options.button_name, options.options)
  ),
  page_menu_dispatch_custom_event: closing_dropdown(dispatch_custom_event),
  page_menu_form_submit: closing_dropdown((_element, options) =>
    form_submit(options.form_name, options.button_name)
  ),
  // The current URL, as the page may have changed its variables since it was rendered
  page_menu_reload_with_vars: (_element, options) => {
    location.href = makeuri(options.vars)
  },
  page_menu_toggle_popup: (_element, options) => toggle_popup(options.popup_id),
  page_menu_toggle_suggestions: closing_dropdown(() => toggle_suggestions()),
  pagetype_add_to_container: closing_dropdown((_element, options) =>
    pagetype_add_to_container(options.page_type, options.page_name)
  ),
  reload_page: () => location.reload(),
  service_discovery_start: closing_dropdown((_element, options) =>
    start_service_discovery(
      options.host_name,
      options.folder_path,
      options.discovery_options,
      options.transid,
      options.request_vars,
      options.waiting_message
    )
  ),
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
  toggle_inline_help: closing_dropdown(() => toggle_inline_help()),
  waiting_flash_message: (_element, options) => {
    waiting_flash_message('top_heading', options.message)
    return true
  }
}

register_click_actions(click_actions)
