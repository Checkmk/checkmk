#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from typing import override

import pytest
from werkzeug.test import create_environ

import cmk.ccc.version as cmk_version
import cmk.gui.pages
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.pages import Page, PageContext, PageEndpoint
from cmk.utils import paths


def test_registered_pages() -> None:
    expected_pages = [
        "add_bookmark",
        "ajax_bi_rule_preview",
        "ajax_bi_aggregation_preview",
        "ajax_cascading_render_painer_parameters",
        "ajax_activation_state",
        "ajax_add_visual",
        "ajax_backup_job_state",
        "ajax_background_job_details",
        "ajax_acknowledge_user_message",
        "ajax_delete_user_message",
        "ajax_get_user_messages",
        "ajax_user_message_action",
        "ajax_dict_host_tag_condition_get_choice",
        "ajax_fetch_ca",
        "ajax_inv_render_tree",
        "ajax_nagvis_maps_snapin",
        "ajax_ping_host",
        "ajax_popup_action_menu",
        "ajax_popup_host_action_menu",
        "ajax_popup_service_action_menu",
        "ajax_popup_add_visual",
        "ajax_popup_icon_selector",
        "ajax_popup_move_to_folder",
        "ajax_reschedule",
        "ajax_request_ms_graph_access_token",
        "ajax_search",
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
        "ajax_validate_filter",
        "ajax_visual_filter_list_get_choice",
        "ajax_vs_autocomplete",
        "ajax_vs_unit_resolver",
        "ajax_fetch_aggregation_data",
        "ajax_save_bi_aggregation_layout",
        "ajax_sidebar_get_messages",
        "ajax_load_bi_aggregation_layout",
        "ajax_delete_bi_aggregation_layout",
        "ajax_fetch_topology",
        "ajax_sidebar_get_number_of_pending_changes",
        "ajax_sidebar_get_sites_and_changes",
        "ajax_unified_search",
        "ajax_mark_step_as_complete",
        "ajax_get_welcome_page_stage_information",
        "automation_login",
        "bi_map",
        "bi_render_tree",
        "bi_save_treestate",
        "bi_set_assumption",
        "bookmark_lists",
        "change_log",
        "clear_failed_notifications",
        "create_view",
        "create_view_infos",
        "custom_snapins",
        "edit_custom_snapin",
        "pagetype_topics",
        "edit_pagetype_topic",
        "dashboard",
        "download_agent_output",
        "download_crash_report",
        "download_diagnostics_dump",
        "edit_bookmark_list",
        "edit_dashboard",
        "edit_dashboards",
        "edit_view",
        "edit_views",
        "export_views",
        "fetch_agent_output",
        "crash",
        "host_inv_api",
        "host_service_graph_popup",
        "index",
        "login",
        "logout",
        "logwatch",
        "mobile",
        "mobile_view",
        "noauth:automation",
        "message",
        "prediction_graph",
        "parent_child_topology",
        "network_topology",
        "search_open",
        "set_all_sites",
        "side",
        "sidebar_add_snapin",
        "sidebar_ajax_add_snapin",
        "sidebar_ajax_set_snapin_site",
        "sidebar_ajax_speedometer",
        "sidebar_ajax_tag_tree",
        "sidebar_ajax_tag_tree_enter",
        "sidebar_ajax_get_available_snapins",
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
        "user_totp_register",
        "user_two_factor_overview",
        "user_two_factor_enforce",
        "user_two_factor_edit_credential",
        "user_webauthn_register_complete",
        "user_login_two_factor",
        "user_webauthn_login_complete",
        "user_webauthn_login_begin",
        "view",
        "widget_edit_view",
        "widget_figure",
        "widget_graph",
        "widget_iframe_sidebar",
        "widget_iframe_view",
        "wato",
        "wato_ajax_diag_cmk_agent",
        "wato_ajax_diag_host",
        "wato_ajax_execute_check",
        "wato_ajax_fetch_site_status",
        "wato_ajax_profile_repl",
        "welcome",
        "werk",
        "ajax_graph",
        "ajax_graph_hover",
        "ajax_render_graph_content",
        "ajax_initial_view_filters",
        "ajax_initial_topology_filters",
        "ajax_graph_images",
        "gui_timings",
        "download_telemetry",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
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
            "ajax_ntop_ifid",
            "licensing_download_verification_request",
            "noauth:saml_acs",
            "noauth:saml_metadata",
            "noauth:saml_sso",
            "robotmk_suite_log",
            "robotmk_suite_report",
            "download_robotmk_suite_report",
            "ajax_fetch_metric_color",
            "ajax_fetch_ajax_graph",
        ]

    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CLOUD:
        expected_pages += [
            "ajax_saas_onboarding_button_toggle",
            "noauth:cognito_sso",
            "noauth:cognito_callback",
            "cognito_logout",
            "noauth:download_license_request",
            "noauth:upload_license_response",
            "noauth:download_license_usage",
        ]

    # TODO: Depending on how we call the test (single test or whole package) we
    # see this page or we don't...
    actual_set = {p for p in cmk.gui.pages.page_registry.keys() if p != "switch_customer"}  #

    expected_set = set(expected_pages)
    differences = actual_set.symmetric_difference(expected_set)
    if differences:
        sys.stdout.write("Registered pages differ\n")
        sys.stdout.write("Expected but missing: %s\n" % ", ".join(expected_set - actual_set))
        sys.stdout.write("Unknown new pages: %s\n" % ", ".join(actual_set - expected_set))
    assert len(differences) == 0


@pytest.mark.usefixtures("monkeypatch")
def test_page_registry_register_page(capsys: pytest.CaptureFixture[str]) -> None:
    page_registry = cmk.gui.pages.PageRegistry()

    class PageClass(cmk.gui.pages.Page):
        @override
        def page(self, ctx: PageContext) -> None:
            sys.stdout.write("234")

    page_registry.register(PageEndpoint("234handler", PageClass()))

    endpoint = page_registry.get("234handler")
    assert isinstance(endpoint, PageEndpoint)
    handler = endpoint.handler
    assert isinstance(handler, Page)

    handler.handle_page(
        PageContext(
            config=Config(),
            request=Request(create_environ()),
        )
    )
    assert capsys.readouterr()[0] == "234"


def test_page_registry_register_page_handler(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    page_registry = cmk.gui.pages.PageRegistry()

    def page(ctx: PageContext) -> None:
        sys.stdout.write("234")

    page_registry.register(PageEndpoint("234handler", page))

    endpoint = page_registry.get("234handler")
    assert isinstance(endpoint, PageEndpoint)
    handler = endpoint.handler
    assert not isinstance(handler, Page)

    handler(
        PageContext(
            config=Config(),
            request=Request(create_environ()),
        )
    )
    assert capsys.readouterr()[0] == "234"


def test_get_page_handler_default() -> None:
    def dummy(ctx: PageContext) -> None:
        pass

    handler = cmk.gui.pages.get_page_handler("123handler", dummy)
    assert handler is dummy
