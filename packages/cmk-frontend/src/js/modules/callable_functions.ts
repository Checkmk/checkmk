/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable import-x/no-namespace -- Lazily resolved to avoid import cycles */
import * as forms from '@/modules/forms'
import { insert_before } from '@/modules/layout'
import * as page_menu from '@/modules/page_menu'
import { render_qr_code } from '@/modules/qrcode_rendering'
import * as selection from '@/modules/selection'
import { lock_and_redirect } from '@/modules/sites'
import { render_stats_table } from '@/modules/tracking_display'
import * as utils from '@/modules/utils'

import { type CallableFunction, register_callable_functions } from './ts_function_dispatcher'

// See cmk.gui.htmllib.generator:KnownTSFunction
// The type on the Python side and the available keys in this dictionary MUST MATCH.
const callable_functions: { [name: string]: CallableFunction } = {
  render_stats_table: render_stats_table,
  render_qr_code: render_qr_code,
  insert_before: insert_before,
  lock_and_redirect: lock_and_redirect,
  confirm_on_form_leave: (node, options) => forms.confirm_on_form_leave(node, options),

  // utils
  set_focus_by_name: (_node, options) =>
    utils.set_focus_by_name(options.form_name, options.field_name),
  set_focus_by_id: (_node, options) => utils.set_focus_by_id(options.dom_id),
  set_reload: (_node, options) => utils.set_reload(options.secs, options.url ?? undefined),
  reload_whole_page: (_node, options) => utils.reload_whole_page(options.url),
  navigate_to_page: (_node, options) => utils.navigate_to_page(options.url),
  update_row_info: (_node, options) => utils.update_row_info(options.text),
  set_inpage_search_result_info: (_node, options) =>
    utils.set_inpage_search_result_info(options.text),
  update_time: (_node, options) => utils.update_time(options.target, options.time),
  fade_out_element: (_node, options) =>
    utils.fade_out_element(options.element_id, options.delay_ms, options.selector),

  // page_menu
  enable_menu_entry: (_node, options) => page_menu.enable_menu_entry(options.id, options.enabled),
  enable_menu_entries: (_node, options) =>
    page_menu.enable_menu_entries(options.css_class, options.enabled),
  check_menu_entry_by_checkboxes: (_node, options) =>
    page_menu.check_menu_entry_by_checkboxes(options.id),
  toggle_navigation_page_menu_entry: () => page_menu.toggle_navigation_page_menu_entry(),
  inpage_search_init: (_node, options) =>
    page_menu.inpage_search_init(options.reset_button_id, options.was_submitted, options.reset_url),
  open_popup: (_node, options) => page_menu.open_popup(options.popup_id),
  form_submit: (_node, options) => page_menu.form_submit(options.form_name, options.button_name),
  fetch_hot_menu_entries: (_node, options) =>
    page_menu.fetch_hot_menu_entries(options.url, options.entry_names),
  init_filter_form: (_node, options) => page_menu.init_filter_form(options.filter_list_selected_id),

  // forms
  confirm_dialog_redirect: (_node, options) =>
    forms.confirm_dialog(
      options.dialog_options,
      () => {
        location.href = options.confirm_url
      },
      options.cancel_url ? () => (location.href = options.cancel_url) : null,
      null,
      options.post_confirm_waiting_text ?? null
    ),
  confirm_dialog_form_submit: (_node, options) =>
    forms.confirm_dialog_form_submit(
      options.dialog_options,
      options.form_id,
      options.cancel_url,
      options.deny_popup_id ? () => page_menu.toggle_popup(options.deny_popup_id) : null
    ),

  // selection
  set_selection_enabled: (_node, options) => selection.set_selection_enabled(options.enabled),
  init_rowselect: (_node, options) => selection.init_rowselect(options.properties),
  update_bulk_moveto: (_node, options) => selection.update_bulk_moveto(options.value)
}

register_callable_functions(callable_functions)
