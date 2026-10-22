/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KnownClickAction } from 'cmk-shared-typing/typescript/legacy_frontend_hooks'

import { activate_changes } from '@/modules/activation'
import { call_ajax } from '@/modules/ajax'
import { toggle_assumption, toggle_box, toggle_subtree } from '@/modules/bi'
import { toggle as toggle_foldable_container } from '@/modules/foldable_container'
import { confirm_link, waiting_flash_message } from '@/modules/forms'
import { toggle as toggle_inline_help } from '@/modules/help'
import {
  ack_problems_update_expiration_active_state,
  check_menu_entry_by_checkboxes,
  close_active_dropdown,
  close_popup,
  confirmed_form_submit,
  form_submit,
  toggle_popup,
  toggle_popup_filter_list,
  toggle_suggestions,
  update_down_duration_button,
  update_filter_list_scroll
} from '@/modules/page_menu'
import {
  add_to_visual,
  close_popup as close_icon_popup,
  graph_export,
  pagetype_add_to_container,
  toggle_popup as toggle_popup_menu
} from '@/modules/popup_menu'
import { close_popup as close_quicksearch_popup, on_search_click } from '@/modules/quicksearch'
import {
  execute_bulk_action_for_single_host,
  toggle_all_rows,
  toggle_group_rows
} from '@/modules/selection'
import { start as start_service_discovery } from '@/modules/service_discovery'
import {
  add_bookmark,
  switch_customer,
  switch_site,
  update_vue_snapin_contents,
  virtual_host_tree_enter,
  wato_tree_click
} from '@/modules/sidebar'
import { details_period_click } from '@/modules/sla'
import {
  acknowledge_user_message,
  copy_dom_element_content_to_clipboard,
  copy_to_clipboard,
  delete_user_message,
  makeLoadingTransition,
  makeuri,
  querySelectorID,
  reload_whole_page,
  toggle_more,
  update_time
} from '@/modules/utils'
import { listof_entry_index } from '@/modules/valuespec_listof'
import {
  duallist_switch,
  iconselector_select,
  iconselector_toggle,
  iconselector_toggle_names,
  label_group_delete,
  list_choice_toggle_all,
  listof_add,
  listof_delete,
  listof_sort,
  listofmultiple_add,
  listofmultiple_del,
  passwordspec_randomize,
  rule_comment_prefix_date_and_user,
  toggle_hidden,
  toggle_option,
  visual_filter_list_reset
} from '@/modules/valuespecs'
import {
  add_to_visual as add_view_to_visual,
  reschedule_check,
  toggle_grouped_rows
} from '@/modules/views'
import {
  fix_visibility,
  open_folder,
  randomize_secret,
  toggle_attribute,
  toggle_container,
  toggle_test_notification_visibility
} from '@/modules/wato'

import {
  type ClickAction,
  type ClickActionArguments,
  register_click_actions
} from './click_action_dispatcher'

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

const dispatch_custom_event: ClickAction = (_element, options) => {
  const custom_event = () => new CustomEvent(options.name, { detail: options.detail })
  document.dispatchEvent(custom_event())
  if (options.to_parent === true && window.parent !== window) {
    window.parent.document.dispatchEvent(custom_event())
  }
}

function toggle_foldable_container_by_options(options: ClickActionArguments) {
  toggle_foldable_container(
    options.treename,
    options.id,
    options.fetch_url,
    options.save_state === 'true'
  )
}

const click_actions: Record<KnownClickAction, ClickAction> = {
  ack_problems_update_expiration_active_state: (element) => {
    ack_problems_update_expiration_active_state(element as HTMLInputElement)
    // Keep toggling the checkbox
    return true
  },
  activate_changes: closing_dropdown((_element, options) =>
    activate_changes(options.mode, options.site_id)
  ),
  add_bookmark: () => add_bookmark(),
  add_to_visual: closing_dropdown((_element, options) =>
    add_to_visual(options.visual_type, options.visual_name)
  ),
  bi_toggle_assumption: (element, options) =>
    toggle_assumption(element, options.site!, options.host!, options.service!),
  bi_toggle_box: (element, options) => toggle_box(element, options.lazy === 'true'),
  bi_toggle_subtree: (element, options) => toggle_subtree(element, options.lazy === 'true'),
  confirm_link: (_element, options) => {
    confirm_link(options.url, options.message, options.options, options.post_confirm_waiting_text)
    close_icon_popup()
  },
  confirmed_form_submit_for_single_host: (element, options) => {
    execute_bulk_action_for_single_host(element, confirmed_form_submit as () => void, [
      options.form_name!,
      options.button_name!,
      JSON.parse(options.options!)
    ])
    close_icon_popup()
  },
  copy_dom_element_content_to_clipboard: (_element, options) =>
    copy_dom_element_content_to_clipboard(options.node_id!, options.success_msg),
  copy_to_clipboard: (_element, options) => copy_to_clipboard(options.text!, options.success_msg),
  dispatch_custom_event: dispatch_custom_event,
  downtime_duration_select: (_element, options) => {
    update_down_duration_button(options.id!)
    update_time('date__down_from_date', options.from_date!)
    update_time('time__down_from_time', options.from_time!)
    update_time('date__down_to_date', options.to_date!)
    update_time('time__down_to_time', options.to_time!)
  },
  foldable_container_toggle: (_element, options) => {
    toggle_foldable_container_by_options(options)
    // The header may contain links, e.g. to a view, which have to be followed
    return true
  },
  follow_url: (_element, options) => {
    location.href = options.url!
    // Links inside the element, e.g. in a table header, still take precedence
    return true
  },
  form_submit_for_single_host: (element, options) =>
    execute_bulk_action_for_single_host(element, form_submit as () => void, [
      options.form_name!,
      options.button_name!
    ]),
  graph_export: closing_dropdown((_element, options) => graph_export(options.page)),
  icon_loading_button: (element, options) => {
    // Prevent starting several long-running actions in parallel before the navigation completes
    for (const button of document.getElementsByClassName(
      'icon_loading_button'
    ) as HTMLCollectionOf<HTMLElement>) {
      delete button.dataset.cmk_on_click
      button.style.pointerEvents = 'none'
      if (button !== element) {
        button.style.opacity = '0.5'
      }
    }
    const img = element.getElementsByTagName('img')[0]
    if (img) {
      img.src = img.src.replace(/facelift\/images\/.+$/, 'facelift/images/load_graph.png')
    }
    waiting_flash_message('page_menu_popups', options.waiting_message!)
    location.href = options.url!
  },
  loading_button: (element, options) => {
    if (options.waiting_message) {
      waiting_flash_message('page_menu_popups', options.waiting_message)
    }
    if (options.remove_parent === 'true') {
      element.parentElement?.remove()
    }
    location.href = options.url!
    // Only navigate once
    delete element.dataset.cmk_on_click
  },
  loading_transition: (_element, options, event) => {
    makeLoadingTransition(
      options.template || null,
      options.delay_ms ? parseInt(options.delay_ms) : 1000,
      options.title,
      event
    )
    // Follow the link inside the element
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
  page_menu_check_entry_by_checkboxes: (_element, options) => {
    check_menu_entry_by_checkboxes(options.id!)
    // Keep toggling the checkbox
    return true
  },
  page_menu_close_popup: (element, options) => {
    close_popup(element as HTMLAnchorElement)
    if (options.reset_input_id) {
      ;(document.getElementById(options.reset_input_id) as HTMLInputElement).value = ''
    }
  },
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
  page_menu_toggle_popup_filter_list: (element, options) =>
    toggle_popup_filter_list(element as HTMLAnchorElement, options.filter_list_id!),
  page_menu_toggle_suggestions: closing_dropdown(() => toggle_suggestions()),
  pagetype_add_to_container: closing_dropdown((_element, options) =>
    pagetype_add_to_container(options.page_type, options.page_name)
  ),
  popup_menu_toggle: (element, options, event) => {
    toggle_popup_menu(
      event,
      element,
      options.ident!,
      JSON.parse(options.method!),
      JSON.parse(options.data!),
      options.resizable === 'true'
    )
  },
  quicksearch_close_popup: () => {
    close_quicksearch_popup()
    // Clicks on the search results have to be followed
    return true
  },
  quicksearch_search: () => {
    on_search_click()
    // The button is inside the search field container, which closed the popup afterwards
    close_quicksearch_popup()
  },
  randomize_secret: (_element, options) =>
    randomize_secret(options.id, options.length, options.message),
  reload_page: () => location.reload(),
  reload_page_with_message: (element, options) => {
    element.textContent = options.message!
    location.reload()
  },
  selection_toggle_all_rows: (element, options) => {
    toggle_all_rows(
      options.in_form === 'true' ? ((element as HTMLInputElement).form ?? undefined) : undefined
    )
    if (options.menu_entry_id) {
      check_menu_entry_by_checkboxes(options.menu_entry_id)
    }
  },
  selection_toggle_group_rows: (element) => toggle_group_rows(element as HTMLInputElement),
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
  sla_details_period_click: (element, options) =>
    details_period_click(element as HTMLTableCellElement, options.sla_period!),
  switch_customer: (_element, options) => {
    switch_customer(options.customer_id, options.switch_state)
    switch_site(options.url)
  },
  switch_master_state: (_element, options) => {
    call_ajax(options.url, {
      method: 'POST',
      response_handler: update_vue_snapin_contents,
      handler_data: 'snapin_master_control'
    })
  },
  switch_site: (_element, options) => switch_site(options.url),
  toggle_all_rows: closing_dropdown(() =>
    toggle_all_rows(querySelectorID('main_page_content') ?? undefined)
  ),
  toggle_inline_help: closing_dropdown(() => toggle_inline_help()),
  toggle_more: (element, options) =>
    toggle_more(element, options.id!, parseInt(options.dom_levels_up!)),
  toggle_test_notification_visibility: (_element, options) =>
    toggle_test_notification_visibility(
      options.source!,
      options.target!,
      options.hide_options === 'true'
    ),
  user_message_acknowledge: (_element, options) => {
    acknowledge_user_message(options.id!)
    reload_whole_page()
  },
  user_message_delete: (element, options) => {
    delete_user_message(options.id!, element as HTMLButtonElement)
    if (options.reload === 'true') {
      reload_whole_page()
    }
  },
  valuespec_duallist_switch: (_element, options) =>
    duallist_switch(options.field_suffix, options.varprefix, options.keeporder ? 1 : 0),
  valuespec_iconselector_select: (_element, options, event) =>
    iconselector_select(event!, options.varprefix!, options.icon!),
  valuespec_iconselector_toggle: (_element, options) =>
    iconselector_toggle(options.varprefix, options.category_name),
  valuespec_iconselector_toggle_names: (_element, options, event) =>
    iconselector_toggle_names(event!, options.varprefix!),
  valuespec_label_group_delete: (element, options) =>
    label_group_delete(
      options.varprefix!,
      listof_entry_index(element, options.varprefix!),
      JSON.parse(options.first_elem_choices_or_label!),
      options.show_empty_group_by_default === 'true'
    ),
  valuespec_list_choice_toggle_all: (_element, options) =>
    list_choice_toggle_all(options.varprefix),
  valuespec_listof_add: (_element, options) =>
    listof_add(options.varprefix!, options.magic!, options.style!),
  valuespec_listof_delete: (element, options) =>
    listof_delete(options.varprefix!, listof_entry_index(element, options.varprefix!)),
  valuespec_listof_sort: (_element, options) =>
    listof_sort(options.varprefix!, options.magic!, parseInt(options.sort_by!)),
  valuespec_listofmultiple_add: (element, options) => {
    if (options.filter_list_id) {
      // A choice in the filter list popup of a view
      listofmultiple_add(
        options.varprefix!,
        options.choice_page_name!,
        JSON.parse(options.page_request_vars!),
        element as HTMLAnchorElement
      )
      update_filter_list_scroll(options.filter_list_id)
    } else {
      listofmultiple_add(
        options.varprefix!,
        options.choice_page_name!,
        JSON.parse(options.page_request_vars!)
      )
    }
  },
  valuespec_listofmultiple_delete: (_element, options) =>
    listofmultiple_del(options.varprefix!, options.ident!),
  valuespec_password_randomize: (element, options) =>
    passwordspec_randomize(element as HTMLAnchorElement, parseInt(options.length!)),
  valuespec_password_toggle_hidden: (element) => toggle_hidden(element as HTMLAnchorElement),
  valuespec_rule_comment_prefix: (element, options) =>
    rule_comment_prefix_date_and_user(element as HTMLAnchorElement, options.text!),
  valuespec_toggle_option: (element, options) => {
    toggle_option(element as HTMLInputElement, options.div_id!, options.negate === 'true' ? 1 : 0)
    // Keep toggling the checkbox
    return true
  },
  valuespec_visual_filter_list_reset: (_element, options) =>
    visual_filter_list_reset(
      options.varprefix!,
      JSON.parse(options.page_request_vars!),
      options.page_name!,
      options.reset_ajax_page!,
      JSON.parse(options.context!)
    ),
  views_add_to_visual: (_element, options) =>
    add_view_to_visual(
      options.visual_type!,
      options.visual_name!,
      options.source_type!,
      JSON.parse(options.context!)
    ),
  views_reschedule_check: (element, options) =>
    reschedule_check(element, options.site!, options.host!, options.service!, options.wait_svc!),
  views_toggle_grouped_rows: (element, options) => {
    toggle_grouped_rows(
      options.tree!,
      options.id!,
      element as HTMLTableCellElement,
      parseInt(options.num_rows!)
    )
    // Links in the group title have to be followed
    return true
  },
  virtual_host_tree_enter: (_element, options) => virtual_host_tree_enter(options.path),
  waiting_flash_message: (_element, options) => {
    waiting_flash_message('top_heading', options.message)
    return true
  },
  wato_fix_visibility: () => {
    fix_visibility()
    // Keep toggling the checkbox
    return true
  },
  wato_open_folder: (_element, options, event) => {
    open_folder(event, options.url!)
    // Links inside the folder, e.g. its edit button, have to be followed
    return true
  },
  wato_toggle_attribute: (element, options) => {
    if (options.fix_visibility === 'true') {
      fix_visibility()
    }
    toggle_attribute(element as HTMLInputElement, options.attrname!)
    // Keep toggling the checkbox
    return true
  },
  wato_toggle_container: (_element, options) => toggle_container(options.id!),
  wato_tree_click: (element, options) => {
    wato_tree_click(options.folder_path)
    // The link is the title of the folder's foldable container, which is toggled by a click, too
    const header = element.parentElement?.closest<HTMLElement>(
      '[data-cmk_on_click="foldable_container_toggle"]'
    )
    if (header?.dataset.cmk_on_click_arguments) {
      toggle_foldable_container_by_options(JSON.parse(header.dataset.cmk_on_click_arguments))
    }
  }
}

register_click_actions(click_actions)
