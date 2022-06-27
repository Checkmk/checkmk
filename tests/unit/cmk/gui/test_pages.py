#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import cmk.utils.version as cmk_version

import cmk.gui.pages


def test_registered_pages() -> None:
    expected_pages = [
        "add_bookmark",
        "ajax_figure_dashlet_data",
        "ajax_bi_rule_preview",
        "ajax_bi_aggregation_preview",
        "ajax_cascading_render_painer_parameters",
        "ajax_activation_state",
        "ajax_add_visual",
        "ajax_autocomplete_labels",
        "ajax_backup_job_state",
        "ajax_background_job_details",
        "ajax_dashlet_pos",
        "ajax_delete_user_message",
        "ajax_dict_host_tag_condition_get_choice",
        "ajax_fetch_ca",
        "ajax_inv_render_tree",
        "ajax_nagvis_maps_snapin",
        "ajax_popup_action_menu",
        "ajax_popup_add_visual",
        "ajax_popup_icon_selector",
        "ajax_popup_move_to_folder",
        "ajax_reschedule",
        "ajax_search",
        "ajax_search_monitoring",
        "ajax_search_setup",
        "ajax_service_discovery",
        "ajax_set_dashboard_start_url",
        "ajax_set_foldertree",
        "ajax_set_rowselection",
        "ajax_sidebar_position",
        "ajax_sidebar_get_unack_incomp_werks",
        "ajax_start_activation",
        "ajax_switch_help",
        "ajax_ui_theme",
        "ajax_userdb_sync",
        "ajax_visual_filter_list_get_choice",
        "ajax_vs_autocomplete",
        "ajax_vs_unit_resolver",
        "ajax_fetch_aggregation_data",
        "ajax_save_bi_template_layout",
        "ajax_save_bi_aggregation_layout",
        "ajax_sidebar_get_messages",
        "ajax_load_bi_template_layout",
        "ajax_load_bi_aggregation_layout",
        "ajax_delete_bi_template_layout",
        "ajax_delete_bi_aggregation_layout",
        "ajax_fetch_topology",
        "ajax_get_all_bi_template_layouts",
        "automation_login",
        "bi_map",
        "bi_render_tree",
        "bi_save_treestate",
        "bi_set_assumption",
        "bookmark_lists",
        "change_log",
        "clear_failed_notifications",
        "create_dashboard",
        "create_view",
        "create_view_dashlet",
        "create_view_dashlet_infos",
        "create_link_view_dashlet",
        "create_view_infos",
        "custom_snapins",
        "edit_custom_snapin",
        "pagetype_topics",
        "edit_pagetype_topic",
        "dashboard",
        "dashboard_dashlet",
        "delete_dashlet",
        "download_agent_output",
        "download_crash_report",
        "download_diagnostics_dump",
        "download_robotmk_report",
        "edit_bookmark_list",
        "edit_dashboard",
        "edit_dashboards",
        "edit_dashlet",
        "clone_dashlet",
        "edit_view",
        "edit_views",
        "export_views",
        "fetch_agent_output",
        "graph_dashlet",
        "crash",
        "host_inv_api",
        "host_service_graph_popup",
        "index",
        "info",
        "login",
        "logout",
        "logwatch",
        "mobile",
        "mobile_view",
        "noauth:automation",
        "noauth:run_cron",
        "message",
        "prediction_graph",
        "parent_child_topology",
        "robotmk",
        "robotmk_report",
        "search_open",
        "side",
        "sidebar_add_snapin",
        "sidebar_ajax_add_snapin",
        "sidebar_ajax_set_snapin_site",
        "sidebar_ajax_speedometer",
        "sidebar_ajax_tag_tree",
        "sidebar_ajax_tag_tree_enter",
        "sidebar_fold",
        "sidebar_message_read",
        "sidebar_move_snapin",
        "sidebar_openclose",
        "sidebar_snapin",
        "switch_master_state",
        "switch_site",
        "tree_openclose",
        "user_change_pw",
        "user_message",
        "user_profile",
        "user_profile_replicate",
        "user_webauthn_register_begin",
        "user_two_factor_overview",
        "user_two_factor_edit_credential",
        "user_webauthn_register_complete",
        "user_login_two_factor",
        "user_webauthn_login_complete",
        "user_webauthn_login_begin",
        "view",
        "wato",
        "wato_ajax_diag_host",
        "wato_ajax_execute_check",
        "wato_ajax_fetch_site_status",
        "wato_ajax_profile_repl",
        "webapi",
        "werk",
        "ajax_graph",
        "ajax_graph_hover",
        "ajax_render_graph_content",
        "ajax_initial_dashboard_filters",
        "ajax_initial_view_filters",
        "ajax_initial_topology_filters",
        "noauth:ajax_graph_images",
    ]

    if not cmk_version.is_raw_edition():
        expected_pages += [
            "ajax_host_overview_tooltip",
            "ajax_pagetype_add_element",
            "ajax_popup_add_metric_to_graph",
            "combined_graphs",
            "create_report",
            "custom_graph",
            "custom_graph_design",
            "custom_graphs",
            "download_agent",
            "download_mkp",
            "download_stored_report",
            "edit_custom_graph",
            "edit_forecast_graph",
            "edit_graph_collection",
            "edit_graph_tuning",
            "edit_report",
            "edit_report_content",
            "edit_report_element",
            "edit_report_fixel",
            "edit_reports",
            "edit_sla_configuration",
            "forecast_editor",
            "forecast_graph",
            "forecast_graphs",
            "graph_collection",
            "graph_collections",
            "graph_export",
            "graph_image",
            "graph_tunings",
            "noauth:deploy_agent",
            "register_agent",
            "report",
            "report_download_preview",
            "report_instant",
            "report_instant_graph_collection",
            "report_scheduler",
            "report_scheduler_edit",
            "report_scheduler_preview",
            "report_store",
            "report_thumbnail",
            "sla_configurations",
            "sla_details",
            "ntop_host_details",
            "ajax_ntop_top_talkers",
            "ajax_ntop_interface_quickstats",
            "ajax_ntop_host_details",
            "ajax_ntop_host_stats",
            "ajax_ntop_host_traffic",
            "ajax_ntop_host_ports",
            "ajax_ntop_host_ports_painter",
            "ajax_ntop_host_protocol_breakdown",
            "ajax_ntop_host_top_peers_protocols",
            "ajax_ntop_host_top_peers_protocols_painter",
            "ajax_ntop_host_top_peers_protocols_bar",
            "ajax_ntop_host_top_peers_protocols_pie",
            "ajax_ntop_host_packets",
            "ajax_ntop_host_applications",
            "ajax_ntop_flows",
            "ajax_ntop_engaged_alerts",
            "ajax_ntop_past_alerts",
            "ajax_ntop_flow_alerts",
            "license_usage_download",
        ]

    # TODO: Depending on how we call the test (single test or whole package) we
    # see this page or we don't...
    actual_set = set(p for p in cmk.gui.pages.page_registry.keys() if p != "switch_customer")  #

    expected_set = set(expected_pages)
    differences = actual_set.symmetric_difference(expected_set)
    if differences:
        sys.stdout.write("Registered pages differ\n")
        sys.stdout.write("Expected but missing: %s\n" % ", ".join(expected_set - actual_set))
        sys.stdout.write("Unknown new pages: %s\n" % ", ".join(actual_set - expected_set))
    assert len(differences) == 0


def test_pages_register(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cmk.gui.pages, "page_registry", cmk.gui.pages.PageRegistry())

    @cmk.gui.pages.register("123handler")
    def page_handler():  # pylint: disable=unused-variable
        sys.stdout.write("123")

    handler = cmk.gui.pages.get_page_handler("123handler")
    assert callable(handler)

    handler()
    assert capsys.readouterr()[0] == "123"


def test_pages_register_handler(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cmk.gui.pages, "page_registry", cmk.gui.pages.PageRegistry())

    class PageClass:
        def handle_page(self) -> None:
            sys.stdout.write("234")

    cmk.gui.pages.register_page_handler("234handler", lambda: PageClass().handle_page())

    handler = cmk.gui.pages.get_page_handler("234handler")
    assert callable(handler)

    handler()
    assert capsys.readouterr()[0] == "234"


def test_page_registry_register_page(monkeypatch, capsys) -> None:
    page_registry = cmk.gui.pages.PageRegistry()

    @page_registry.register_page("234handler")
    class PageClass(cmk.gui.pages.Page):
        def page(self) -> None:
            sys.stdout.write("234")

    handler = page_registry.get("234handler")
    assert handler == PageClass

    handler().handle_page()
    assert capsys.readouterr()[0] == "234"


def test_get_page_handler_default() -> None:
    def dummy():
        pass

    handler = cmk.gui.pages.get_page_handler("123handler", dummy)
    assert handler is dummy
