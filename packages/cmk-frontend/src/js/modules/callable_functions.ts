/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable import-x/no-namespace -- Lazily resolved to avoid import cycles */
import type { KnownTSFunction } from 'cmk-shared-typing/typescript/legacy_frontend_hooks'
import { select } from 'd3'

import * as activation from '@/modules/activation'
import * as background_job from '@/modules/background_job'
import * as backup from '@/modules/backup'
import * as bi from '@/modules/bi'
import * as dashboard from '@/modules/dashboard'
import { figure_registry } from '@/modules/figures/cmk_figures'
import * as forms from '@/modules/forms'
import * as host_diagnose from '@/modules/host_diagnose'
import { insert_before } from '@/modules/layout'
import * as license_usage_timeseries_graph from '@/modules/license_usage/license_usage_timeseries_graph'
import * as nodevis from '@/modules/nodevis/main'
import * as nodevis_utils from '@/modules/nodevis/utils'
import * as ntop_host_details from '@/modules/ntop/ntop_host_details'
import * as ntop_utils from '@/modules/ntop/ntop_utils'
import * as page_menu from '@/modules/page_menu'
import { render_qr_code } from '@/modules/qrcode_rendering'
import * as quicksearch from '@/modules/quicksearch'
import * as selection from '@/modules/selection'
import * as service_discovery from '@/modules/service_discovery'
import * as sidebar from '@/modules/sidebar'
import * as sites from '@/modules/sites'
import { render_stats_table } from '@/modules/tracking_display'
import * as transfer from '@/modules/transfer'
import * as utils from '@/modules/utils'
import * as valuespecs from '@/modules/valuespecs'
import * as wato from '@/modules/wato'

import { run_click_action } from './click_action_dispatcher'
import { type CallableFunction, register_callable_functions } from './ts_function_dispatcher'

const license_usage_graphs: Record<string, (num_graphs: number, aggregation: any) => void> = {
  services: license_usage_timeseries_graph.render_services_usage_graph,
  tests: license_usage_timeseries_graph.render_tests_usage_graph,
  free_tests: license_usage_timeseries_graph.render_free_tests_usage_graph,
  metric_series: license_usage_timeseries_graph.render_metric_series_usage_graph,
  free_metric_series: license_usage_timeseries_graph.render_free_metric_series_usage_graph
}

// The mobile functions are registered by the mobile bundle, see mobile.ts.
const callable_functions: Record<Exclude<KnownTSFunction, `mobile_${string}`>, CallableFunction> = {
  render_stats_table: render_stats_table,
  render_qr_code: render_qr_code,
  insert_before: insert_before,
  lock_and_redirect: sites.lock_and_redirect,
  confirm_on_form_leave: (node, options) => forms.confirm_on_form_leave(node, options),

  // dashboard
  ignore_public_dashboard_clicks: () => dashboard.ignore_public_dashboard_clicks(),
  redirect_shared_dashboard: (_node, options) =>
    dashboard.redirect_shared_dashboard(options.search_name, options.target_url),
  post_message_to_parent: (_node, options) => window.parent.postMessage(options.message),

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
  confirm_dialog_redirect: (node, options) =>
    forms.confirm_dialog(
      options.dialog_options,
      () => {
        if (options.confirm_action) {
          const { action, arguments: args } = options.confirm_action
          run_click_action(action, node, args ?? {})
        } else {
          location.href = options.confirm_url
        }
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
  update_bulk_moveto: (_node, options) => selection.update_bulk_moveto(options.value),

  // valuespecs
  list_of_strings_init: (_node, options) =>
    valuespecs.list_of_strings_init(
      options.varprefix,
      options.split_on_paste,
      options.split_separators
    ),
  listof_update_indices: (_node, options) => valuespecs.listof_update_indices(options.varprefix),
  listofmultiple_init: (_node, options) =>
    valuespecs.listofmultiple_init(options.varprefix, options.was_submitted ?? false),
  add_cascading_sub_valuespec_parameters: (_node, options) =>
    valuespecs.add_cascading_sub_valuespec_parameters(options.varprefix, options.parameters),
  update_unit_selector: (_node, options) =>
    valuespecs.update_unit_selector(options.varprefix, options.metric_ref_prefix),
  init_on_change_validation: (_node, options) =>
    valuespecs.init_on_change_validation(options.varname, options.filter_ident),
  remove_label_filter_hidden_fields: (_node, options) =>
    forms.remove_label_filter_hidden_fields(options.varprefix),
  render_input_range: (_node, options) =>
    nodevis_utils.render_input_range(
      select(options.selector),
      options.range_options,
      options.value
    ),

  // bi
  bi_set_rule_argument_lookup: (_node, options) => bi.set_rule_argument_lookup(options.lookup),
  bi_rule_preview: (_node, options) => {
    new bi.BIRulePreview(options.root_node, options.varprefix)
  },
  bi_aggregation_preview: (_node, options) => {
    new bi.BIAggregationPreview(options.root_node, options.varprefix)
  },
  nodevis_create_example: (_node, options) => {
    new nodevis.example_generator(options.varprefix).create_example(options.value)
  },

  // nodevis
  show_bi_aggregation: (_node, options) =>
    nodevis.show_bi_aggregation(options.div_id, options.aggr_name, options.layout_id),
  show_topology: (_node, options) =>
    nodevis.show_topology(
      options.div_id,
      options.topology_type,
      options.translations,
      options.data
    ),

  // sidebar
  register_search_field: (_node, options) => quicksearch.register_search_field(options.field),
  fetch_nagvis_snapin_contents: () => sidebar.fetch_nagvis_snapin_contents(),
  speedometer_show_speed: (_node, options) =>
    sidebar.speedometer_show_speed(
      options.last_perc,
      options.program_start,
      options.scheduled_rate
    ),

  // misc
  submit_crash_report: (_node, options) =>
    transfer.submit_crash_report(options.url, options.post_data),
  enable_submit_buttons_on_nonempty_input: (_node, options) =>
    forms.enable_submit_buttons_on_nonempty_input(
      document.getElementById(options.input_id) as HTMLInputElement,
      options.button_ids
    ),

  // backup
  refresh_backup_job_details: (_node, options) =>
    backup.refresh_job_details(options.url, options.ident, options.is_site),

  // figures
  show_figure: (_node, options) => {
    const figure = new (figure_registry.get_figure(options.figure_ident))(
      `#${options.div_id}`,
      null
    )
    figure.set_widget_content(options.widget_content)
    figure.initialize()
    figure.process_data(options.data)
  },
  show_ntop_table_figure: (_node, options) => {
    const figure = new (figure_registry.get_figure('table'))(`#${options.div_id}`)
    figure.set_post_url_and_body(options.post_url, options.post_body)
    figure.initialize()
    figure.scheduler.force_update()
  },

  // ntop
  show_ntop_host_details: (_node, options) => {
    const tabs = new ntop_host_details.HostTabs(`#${options.div_id}`)
    tabs.set_current_ntophost(options.host_address)
    tabs.initialize(options.tab, options.ifid, options.vlanid)
  },
  show_ntop_interface_quickstats: (_node, options) => {
    const table = new ntop_utils.interface_table(`#${options.div_id}`)
    table.set_host_address(options.host_address)
    table.set_ifid(options.ifid)
    table.set_vlanid(options.vlanid)
    table.set_post_url_and_body(options.post_url)
    table.initialize()
    table.scheduler.set_update_interval(2)
    table.scheduler.force_update()
  },

  // licensing
  render_license_usage_graph: (_node, options) =>
    license_usage_graphs[options.graph](options.num_graphs, options.aggregation),

  // wato
  replace_error_msg_with_confirm_dialog: () => forms.replace_error_msg_with_confirm_dialog(),
  background_job_start: (_node, options) =>
    background_job.start(options.update_url, options.job_id),
  prepare_edit_dialog: (_node, options) => {
    wato.prepare_edit_dialog(options.dialog_properties)
    wato.fix_visibility()
  },
  show_element_on_click: (_node, options) =>
    utils.show_element_on_click(options.trigger_id, options.target_id),
  host_diagnose_start_test: (_node, options) =>
    host_diagnose.start_test(options.ident, options.hostname, options.transid),
  update_site_activation_state: (_node, options) =>
    activation.update_site_activation_state(options.site_state),
  service_discovery_start: (_node, options) =>
    service_discovery.start(
      options.host_name,
      options.folder_path,
      options.discovery_options,
      options.transid,
      options.request_vars ?? null
    ),
  register_delayed_active_check: (_node, options) =>
    service_discovery.register_delayed_active_check(
      options.site,
      options.folder_path,
      options.hostname,
      options.checktype,
      options.item,
      options.divid
    ),
  fetch_site_status: () => sites.fetch_site_status(),
  wato_message: (_node, options) =>
    wato.message(options.message, options.message_type, options.del_var),
  set_button_loading_state_on_click: (_node, options) =>
    document
      .getElementById(options.button_id)
      ?.addEventListener('click', utils.setButtonLoadingState),
  toggle_test_notification_visibility: (_node, options) =>
    wato.toggle_test_notification_visibility(
      options.source,
      options.target,
      options.hide_options ?? false
    )
}

register_callable_functions(callable_functions)
