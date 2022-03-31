#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from dataclasses import asdict
from pathlib import Path

import pytest

from tests.testlib import is_enterprise_repo, is_managed_repo

from livestatus import SiteConfigurations, SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.config
import cmk.gui.permissions as permissions
from cmk.gui.globals import config
from cmk.gui.permissions import (
    load_dynamic_permissions,
    Permission,
    permission_registry,
    permission_section_registry,
)
from cmk.gui.utils.speaklater import LazyString


def test_default_config_from_plugins():
    expected = [
        "roles",
        "debug",
        "screenshotmode",
        "profile",
        "users",
        "admin_users",
        "guest_users",
        "default_user_role",
        "user_online_maxage",
        "log_levels",
        "slow_views_duration_threshold",
        "multisite_users",
        "multisite_hostgroups",
        "multisite_servicegroups",
        "multisite_contactgroups",
        "sidebar",
        "sidebar_update_interval",
        "sidebar_show_scrollbar",
        "sidebar_notify_interval",
        "quicksearch_dropdown_limit",
        "quicksearch_search_order",
        "failed_notification_horizon",
        "soft_query_limit",
        "hard_query_limit",
        "sound_url",
        "enable_sounds",
        "sounds",
        "view_option_refreshes",
        "view_option_columns",
        "doculink_urlformat",
        "view_action_defaults",
        "custom_links",
        "debug_livestatus_queries",
        "show_livestatus_errors",
        "liveproxyd_enabled",
        "visible_views",
        "hidden_views",
        "service_view_grouping",
        "custom_style_sheet",
        "ui_theme",
        "show_mode",
        "start_url",
        "page_heading",
        "login_screen",
        "reschedule_timeout",
        "filter_columns",
        "default_language",
        "hide_languages",
        "default_ts_format",
        "selection_livetime",
        "auth_by_http_header",
        "table_row_limit",
        "multisite_draw_ruleicon",
        "adhoc_downtime",
        "pagetitle_date_format",
        "staleness_threshold",
        "escape_plugin_output",
        "virtual_host_trees",
        "crash_report_url",
        "crash_report_target",
        "guitests_enabled",
        "bulk_discovery_default_settings",
        "use_siteicons",
        "graph_timeranges",
        "userdb_automatic_sync",
        "user_login",
        "user_connections",
        "default_user_profile",
        "log_logon_failures",
        "lock_on_logon_failures",
        "user_idle_timeout",
        "single_user_session",
        "password_policy",
        "user_localizations",
        "user_icons_and_actions",
        "custom_service_attributes",
        "user_downtime_timeranges",
        "builtin_icon_visibility",
        "trusted_certificate_authorities",
        "mkeventd_enabled",
        "mkeventd_pprint_rules",
        "mkeventd_notify_contactgroup",
        "mkeventd_notify_facility",
        "mkeventd_notify_remotehost",
        "mkeventd_connect_timeout",
        "log_level",
        "log_rulehits",
        "rule_optimizer",
        "mkeventd_service_levels",
        "wato_host_tags",
        "wato_aux_tags",
        "wato_tags",
        "wato_enabled",
        "wato_hide_filenames",
        "wato_hide_hosttags",
        "wato_upload_insecure_snapshots",
        "wato_hide_varnames",
        "wato_hide_help_in_lists",
        "wato_activate_changes_concurrency",
        "wato_max_snapshots",
        "wato_num_hostspecs",
        "wato_num_itemspecs",
        "wato_activation_method",
        "wato_write_nagvis_auth",
        "wato_use_git",
        "wato_hidden_users",
        "wato_user_attrs",
        "wato_host_attrs",
        "wato_read_only",
        "wato_hide_folders_without_read_permissions",
        "wato_pprint_config",
        "wato_icon_categories",
        "wato_activate_changes_comment_mode",
        "rest_api_etag_locking",
        "aggregation_rules",
        "aggregations",
        "host_aggregations",
        "bi_packs",
        "default_bi_layout",
        "bi_layouts",
        "bi_compile_log",
        "bi_precompile_on_demand",
        "bi_use_legacy_compilation",
        "sites",
        "config_storage_format",
        "tags",
    ]

    if is_enterprise_repo():
        expected += [
            "agent_deployment_enabled",
            "agent_deployment_host_selection",
            "agent_deployment_central",
            "agent_deployment_remote",
            "agent_signature_keys",
            "have_combined_graphs",
            "reporting_use",
            "reporting_rangespec",
            "reporting_filename",
            "reporting_view_limit",
            "reporting_font_size",
            "reporting_lineheight",
            "reporting_font_family",
            "reporting_pagesize",
            "reporting_margins",
            "reporting_mirror_margins",
            "reporting_date_format",
            "reporting_time_format",
            "reporting_table_layout",
            "reporting_graph_layout",
            "reporting_email_options",
            "subscription_settings",
            "ntop_connection",
        ]

    if is_managed_repo():
        expected += [
            "customers",
            "current_customer",
        ]

    default_config = cmk.gui.config.get_default_config()
    assert sorted(list(default_config.keys())) == sorted(expected)

    default_config2 = asdict(cmk.gui.config.make_config_object(default_config))
    assert sorted(default_config2.keys()) == sorted(expected)


def test_load_config():
    config_path = Path(cmk.utils.paths.default_config_dir, "multisite.mk")
    config_path.unlink(missing_ok=True)

    cmk.gui.config.load_config()
    assert config.quicksearch_dropdown_limit == 80

    with config_path.open("w") as f:
        f.write("quicksearch_dropdown_limit = 1337\n")
    cmk.gui.config.load_config()
    assert config.quicksearch_dropdown_limit == 1337


@pytest.fixture()
def local_config_plugin():
    config_plugin = cmk.utils.paths.local_web_dir / "plugins" / "config" / "test.py"
    config_plugin.parent.mkdir(parents=True)
    with config_plugin.open("w") as f:
        f.write("ding = 'dong'\n")


@pytest.mark.usefixtures("local_config_plugin")
def test_load_config_respects_local_plugin():
    cmk.gui.config.load_config()
    assert config.ding == "dong"  # type: ignore[attr-defined]


@pytest.mark.usefixtures("local_config_plugin")
def test_load_config_allows_local_plugin_setting():
    with Path(cmk.utils.paths.default_config_dir, "multisite.mk").open("w") as f:
        f.write("ding = 'ding'\n")
    cmk.gui.config.load_config()
    assert config.ding == "ding"  # type: ignore[attr-defined]


def test_registered_permission_sections():
    expected_sections = [
        ("bookmark_list", (50, "Bookmark lists", True)),
        ("custom_snapin", (50, "Custom sidebar elements", True)),
        ("sidesnap", (50, "Sidebar elements", True)),
        ("notification_plugin", (50, "Notification plugins", True)),
        ("wato", (50, "Setup", False)),
        ("background_jobs", (50, "Background jobs", False)),
        ("bi", (50, "BI - Checkmk Business Intelligence", False)),
        ("general", (10, "General Permissions", False)),
        ("mkeventd", (50, "Event Console", False)),
        ("action", (50, "Commands on host and services", True)),
        ("dashboard", (50, "Dashboards", True)),
        ("nagvis", (50, "NagVis", False)),
        ("view", (50, "Views", True)),
        ("icons_and_actions", (50, "Icons", True)),
        ("pagetype_topic", (50, "Topics", True)),
    ]

    if not cmk_version.is_raw_edition():
        expected_sections += [
            ("agent_registration", (50, "Agent registration", False)),
            ("custom_graph", (50, "Custom graphs", True)),
            ("forecast_graph", (50, "Forecast graphs", True)),
            ("graph_collection", (50, "Graph collections", True)),
            ("graph_tuning", (50, "Graph tunings", True)),
            ("sla_configuration", (50, "Service Level Agreements", True)),
            ("report", (50, "Reports", True)),
        ]

    section_names = permission_section_registry.keys()
    assert sorted([s[0] for s in expected_sections]) == sorted(section_names)

    for name, (sort_index, title, do_sort) in expected_sections:
        section = permission_section_registry[name]()
        assert section.title == title
        assert section.sort_index == sort_index
        assert section.do_sort == do_sort


def test_registered_permissions():
    load_dynamic_permissions()

    expected_permissions = [
        "action.acknowledge",
        "action.addcomment",
        "action.clearmodattr",
        "action.customnotification",
        "action.downtimes",
        "action.enablechecks",
        "action.fakechecks",
        "action.notifications",
        "action.remove_all_downtimes",
        "action.reschedule",
        "action.star",
        "action.delete_crash_report",
        "background_jobs.delete_foreign_jobs",
        "background_jobs.delete_jobs",
        "background_jobs.manage_jobs",
        "background_jobs.see_foreign_jobs",
        "background_jobs.stop_foreign_jobs",
        "background_jobs.stop_jobs",
        "bi.see_all",
        "dashboard.main",
        "dashboard.simple_problems",
        "dashboard.checkmk",
        "dashboard.checkmk_host",
        "general.acknowledge_werks",
        "general.act",
        "general.agent_pairing",
        "general.change_password",
        "general.manage_2fa",
        "general.configure_sidebar",
        "general.csv_export",
        "general.delete_foreign_pagetype_topic",
        "general.edit_pagetype_topic",
        "general.edit_foreign_pagetype_topic",
        "general.force_pagetype_topic",
        "general.publish_pagetype_topic",
        "general.publish_to_foreign_groups_pagetype_topic",
        "general.publish_to_groups_pagetype_topic",
        "general.see_user_pagetype_topic",
        "general.delete_foreign_bookmark_list",
        "general.delete_foreign_custom_snapin",
        "general.delete_foreign_dashboards",
        "general.delete_foreign_views",
        "general.disable_notifications",
        "general.edit_bookmark_list",
        "general.edit_custom_snapin",
        "general.edit_dashboards",
        "general.edit_foreign_bookmark_list",
        "general.edit_foreign_dashboards",
        "general.edit_foreign_views",
        "general.edit_foreign_custom_snapin",
        "general.edit_notifications",
        "general.edit_profile",
        "general.edit_user_attributes",
        "general.edit_views",
        "general.force_bookmark_list",
        "general.force_custom_snapin",
        "general.force_dashboards",
        "general.force_views",
        "general.ignore_hard_limit",
        "general.ignore_soft_limit",
        "general.logout",
        "general.message",
        "general.painter_options",
        "general.parent_child_topology",
        "general.publish_bookmark_list",
        "general.publish_to_foreign_groups_bookmark_list",
        "general.publish_to_groups_bookmark_list",
        "general.publish_custom_snapin",
        "general.publish_to_foreign_groups_custom_snapin",
        "general.publish_to_groups_custom_snapin",
        "general.publish_dashboards",
        "general.publish_dashboards_to_foreign_groups",
        "general.publish_dashboards_to_groups",
        "general.publish_views",
        "general.publish_views_to_foreign_groups",
        "general.publish_views_to_groups",
        "general.see_all",
        "general.see_availability",
        "general.see_crash_reports",
        "general.see_failed_notifications",
        "general.see_failed_notifications_24h",
        "general.see_sidebar",
        "general.see_stales_in_tactical_overview",
        "general.see_user_bookmark_list",
        "general.see_user_custom_snapin",
        "general.see_user_dashboards",
        "general.see_user_views",
        "general.server_side_requests",
        "general.use",
        "general.view_option_columns",
        "general.view_option_refresh",
        "icons_and_actions.action_menu",
        "icons_and_actions.aggregation_checks",
        "icons_and_actions.aggregations",
        "icons_and_actions.check_manpage",
        "icons_and_actions.check_period",
        "icons_and_actions.crashed_check",
        "icons_and_actions.custom_action",
        "icons_and_actions.download_agent_output",
        "icons_and_actions.download_snmp_walk",
        "icons_and_actions.icon_image",
        "icons_and_actions.inventory",
        "icons_and_actions.logwatch",
        "icons_and_actions.mkeventd",
        "icons_and_actions.notes",
        "icons_and_actions.perfgraph",
        "icons_and_actions.prediction",
        "icons_and_actions.reschedule",
        "icons_and_actions.robotmk",
        "icons_and_actions.robotmk_error",
        "icons_and_actions.rule_editor",
        "icons_and_actions.stars",
        "icons_and_actions.status_acknowledged",
        "icons_and_actions.status_active_checks",
        "icons_and_actions.status_comments",
        "icons_and_actions.status_downtimes",
        "icons_and_actions.status_flapping",
        "icons_and_actions.status_notification_period",
        "icons_and_actions.status_notifications_enabled",
        "icons_and_actions.status_passive_checks",
        "icons_and_actions.status_service_period",
        "icons_and_actions.status_stale",
        "icons_and_actions.wato",
        "icons_and_actions.parent_child_topology",
        "mkeventd.actions",
        "mkeventd.activate",
        "mkeventd.archive_events_of_hosts",
        "mkeventd.changestate",
        "mkeventd.config",
        "mkeventd.delete",
        "mkeventd.edit",
        "mkeventd.see_in_tactical_overview",
        "mkeventd.seeall",
        "mkeventd.seeunrelated",
        "mkeventd.switchmode",
        "mkeventd.update",
        "mkeventd.update_comment",
        "mkeventd.update_contact",
        "nagvis.*_*_*",
        "nagvis.Map_delete",
        "nagvis.Map_delete_*",
        "nagvis.Map_edit",
        "nagvis.Map_edit_*",
        "nagvis.Map_view",
        "nagvis.Map_view_*",
        "nagvis.Rotation_view_*",
        "notification_plugin.asciimail",
        "notification_plugin.cisco_webex_teams",
        "notification_plugin.jira_issues",
        "notification_plugin.mail",
        "notification_plugin.mkeventd",
        "notification_plugin.opsgenie_issues",
        "notification_plugin.pagerduty",
        "notification_plugin.pushover",
        "notification_plugin.servicenow",
        "notification_plugin.signl4",
        "notification_plugin.ilert",
        "notification_plugin.slack",
        "notification_plugin.sms",
        "notification_plugin.sms_api",
        "notification_plugin.spectrum",
        "notification_plugin.victorops",
        "sidesnap.admin_mini",
        "sidesnap.biaggr_groups",
        "sidesnap.biaggr_groups_tree",
        "sidesnap.bookmarks",
        "sidesnap.dashboards",
        "sidesnap.hostgroups",
        "sidesnap.master_control",
        "sidesnap.mkeventd_performance",
        "sidesnap.nagvis_maps",
        "sidesnap.performance",
        "sidesnap.search",
        "sidesnap.servicegroups",
        "sidesnap.sitestatus",
        "sidesnap.speedometer",
        "sidesnap.tactical_overview",
        "sidesnap.tag_tree",
        "sidesnap.time",
        "sidesnap.views",
        "sidesnap.wato_foldertree",
        "view.aggr_all",
        "view.aggr_all_api",
        "view.aggr_group",
        "view.aggr_host",
        "view.aggr_hostgroup_boxed",
        "view.aggr_hostnameaggrs",
        "view.aggr_hostproblems",
        "view.aggr_problems",
        "view.aggr_service",
        "view.aggr_single",
        "view.aggr_single_api",
        "view.aggr_singlehost",
        "view.aggr_singlehosts",
        "view.aggr_summary",
        "view.alerthandlers",
        "view.alertstats",
        "view.allhosts",
        "view.allservices",
        "view.bi_map_hover_host",
        "view.bi_map_hover_service",
        "view.api_downtimes",
        "view.comments",
        "view.comments_of_host",
        "view.comments_of_service",
        "view.contactnotifications",
        "view.crash_reports",
        "view.downtime_history",
        "view.downtimes",
        "view.downtimes_of_host",
        "view.downtimes_of_service",
        "view.docker_containers",
        "view.docker_nodes",
        "view.vpshere_vms",
        "view.vsphere_servers",
        "view.ec_event",
        "view.ec_event_mobile",
        "view.ec_events",
        "view.ec_events_mobile",
        "view.ec_events_of_host",
        "view.ec_events_of_monhost",
        "view.ec_history_of_event",
        "view.ec_history_of_host",
        "view.ec_history_recent",
        "view.ec_historyentry",
        "view.events",
        "view.events_dash",
        "view.failed_notifications",
        "view.host",
        "view.host_crit",
        "view.host_dt_hist",
        "view.host_export",
        "view.host_ok",
        "view.host_pending",
        "view.host_unknown",
        "view.host_warn",
        "view.hostevents",
        "view.hostgroup",
        "view.hostgroup_up",
        "view.hostgroup_down",
        "view.hostgroup_unreach",
        "view.hostgroup_pend",
        "view.hostgroups",
        "view.hostgroupservices",
        "view.hostgroupservices_ok",
        "view.hostgroupservices_warn",
        "view.hostgroupservices_crit",
        "view.hostgroupservices_unknwn",
        "view.hostgroupservices_pend",
        "view.hostnotifications",
        "view.hostpnp",
        "view.hostproblems",
        "view.hostproblems_dash",
        "view.hosts",
        "view.hoststatus",
        "view.hostsvcevents",
        "view.hostsvcnotifications",
        "view.inv_host",
        "view.inv_host_history",
        "view.inv_hosts_cpu",
        "view.inv_hosts_ports",
        "view.invbackplane_of_host",
        "view.invbackplane_search",
        "view.invchassis_of_host",
        "view.invchassis_search",
        "view.invcmksites_of_host",
        "view.invcmksites_search",
        "view.invcmkversions_of_host",
        "view.invcmkversions_search",
        "view.invcontainer_of_host",
        "view.invcontainer_search",
        "view.invdockercontainers_of_host",
        "view.invdockercontainers_search",
        "view.invdockerimages_of_host",
        "view.invdockerimages_search",
        "view.invfan_of_host",
        "view.invfan_search",
        "view.invibmmqchannels_of_host",
        "view.invibmmqchannels_search",
        "view.invibmmqmanagers_of_host",
        "view.invibmmqmanagers_search",
        "view.invibmmqqueues_of_host",
        "view.invibmmqqueues_search",
        "view.invinterface_of_host",
        "view.invinterface_search",
        "view.invkernelconfig_of_host",
        "view.invkernelconfig_search",
        "view.invmodule_of_host",
        "view.invmodule_search",
        "view.invoradataguardstats_of_host",
        "view.invoradataguardstats_search",
        "view.invorainstance_of_host",
        "view.invorainstance_search",
        "view.invorarecoveryarea_of_host",
        "view.invorarecoveryarea_search",
        "view.invorasga_of_host",
        "view.invorasga_search",
        "view.invorapga_of_host",
        "view.invorapga_search",
        "view.invoratablespace_of_host",
        "view.invoratablespace_search",
        "view.invorasystemparameter_of_host",
        "view.invorasystemparameter_search",
        "view.invother_of_host",
        "view.invother_search",
        "view.invpsu_of_host",
        "view.invpsu_search",
        "view.invsensor_of_host",
        "view.invsensor_search",
        "view.invstack_of_host",
        "view.invstack_search",
        "view.invswpac_of_host",
        "view.invswpac_search",
        "view.invtunnels_of_host",
        "view.invtunnels_search",
        "view.invunknown_of_host",
        "view.invunknown_search",
        "view.logfile",
        "view.mobile_contactnotifications",
        "view.mobile_events",
        "view.mobile_host",
        "view.mobile_hostproblems",
        "view.mobile_hostproblems_unack",
        "view.mobile_hoststatus",
        "view.mobile_hostsvcevents",
        "view.mobile_hostsvcnotifications",
        "view.mobile_notifications",
        "view.mobile_searchhost",
        "view.mobile_searchsvc",
        "view.mobile_service",
        "view.mobile_svcevents",
        "view.mobile_svcnotifications",
        "view.mobile_svcproblems",
        "view.mobile_svcproblems_unack",
        "view.nagstamon_hosts",
        "view.nagstamon_svc",
        "view.notifications",
        "view.pending_discovery",
        "view.pendingsvc",
        "view.perf_matrix",
        "view.perf_matrix_search",
        "view.problemsofhost",
        "view.recentsvc",
        "view.searchhost",
        "view.searchpnp",
        "view.searchsvc",
        "view.service",
        "view.service_check_durations",
        "view.servicedesc",
        "view.servicedescpnp",
        "view.servicegroup",
        "view.sitehosts",
        "view.sitesvcs",
        "view.sitesvcs_crit",
        "view.sitesvcs_ok",
        "view.sitesvcs_pend",
        "view.sitesvcs_unknwn",
        "view.sitesvcs_warn",
        "view.stale_hosts",
        "view.svc_dt_hist",
        "view.svcevents",
        "view.svcgroups",
        "view.svcnotifications",
        "view.svcproblems",
        "view.svcproblems_dash",
        "view.topology_hover_host",
        "view.topology_filters",
        "view.uncheckedsvc",
        "view.unmonitored_services",
        "wato.activate",
        "wato.activateforeign",
        "wato.add_or_modify_executables",
        "wato.all_folders",
        "wato.analyze_config",
        "wato.api_allowed",
        "wato.auditlog",
        "wato.automation",
        "wato.backups",
        "wato.bi_admin",
        "wato.bi_rules",
        "wato.check_plugins",
        "wato.clear_auditlog",
        "wato.clone_hosts",
        "wato.custom_attributes",
        "wato.diag_host",
        "wato.diagnostics",
        "wato.download_agent_output",
        "wato.download_agents",
        "wato.edit",
        "wato.edit_all_passwords",
        "wato.edit_all_predefined_conditions",
        "wato.edit_folders",
        "wato.edit_hosts",
        "wato.global",
        "wato.groups",
        "wato.hosts",
        "wato.hosttags",
        "wato.icons",
        "wato.manage_folders",
        "wato.manage_hosts",
        "wato.move_hosts",
        "wato.notifications",
        "wato.parentscan",
        "wato.passwords",
        "wato.pattern_editor",
        "wato.random_hosts",
        "wato.rename_hosts",
        "wato.rulesets",
        "wato.see_all_folders",
        "wato.seeall",
        "wato.service_discovery_to_ignored",
        "wato.service_discovery_to_monitored",
        "wato.service_discovery_to_removed",
        "wato.service_discovery_to_undecided",
        "wato.services",
        "wato.set_read_only",
        "wato.sites",
        "wato.snapshots",
        "wato.timeperiods",
        "wato.update_dns_cache",
        "wato.use",
        "wato.users",
        "wato.show_last_user_activity",
        "view.cmk_servers",
        "view.cmk_sites",
        "view.cmk_sites_of_host",
        "view.host_graphs",
        "view.service_graphs",
    ]

    if not cmk_version.is_raw_edition():
        expected_permissions += [
            "agent_registration.edit",
            "dashboard.linux_hosts_overview",
            "dashboard.linux_single_overview",
            "dashboard.windows_hosts_overview",
            "dashboard.windows_single_overview",
            "dashboard.problems",
            "dashboard.site",
            "dashboard.ntop_alerts",
            "dashboard.ntop_flows",
            "dashboard.ntop_top_talkers",
            "general.edit_reports",
            "icons_and_actions.agent_deployment",
            "icons_and_actions.status_shadow",
            "report.bi_availability",
            "report.default",
            "report.host",
            "report.instant",
            "report.instant_availability",
            "report.instant_graph_collection",
            "report.instant_view",
            "report.service_availability",
            "report.host_performance_graphs",
            "sidesnap.cmc_stats",
            "sidesnap.reports",
            "view.allhosts_deploy",
            "view.ntop_interfaces",
            "wato.agent_deploy_custom_files",
            "wato.agent_deployment",
            "wato.agents",
            "wato.alert_handlers",
            "wato.bake_agents",
            "wato.dcd_connections",
            "wato.download_all_agents",
            "wato.license_usage",
            "wato.influxdb_connections",
            "wato.submit_license_usage",
            "wato.manage_mkps",
            "wato.mkps",
            "wato.sign_agents",
            "general.delete_foreign_custom_graph",
            "general.delete_foreign_forecast_graph",
            "general.delete_foreign_graph_collection",
            "general.delete_foreign_graph_tuning",
            "general.delete_foreign_reports",
            "general.delete_foreign_sla_configuration",
            "general.delete_foreign_stored_report",
            "general.delete_stored_report",
            "general.edit_custom_graph",
            "general.edit_forecast_graph",
            "general.edit_foreign_forecast_graph",
            "general.edit_foreign_custom_graph",
            "general.edit_foreign_graph_collection",
            "general.edit_foreign_graph_tuning",
            "general.edit_foreign_reports",
            "general.edit_foreign_sla_configuration",
            "general.edit_graph_collection",
            "general.edit_graph_tuning",
            "general.edit_sla_configuration",
            "general.force_custom_graph",
            "general.publish_forecast_graph",
            "general.force_graph_collection",
            "general.force_graph_tuning",
            "general.publish_graph_collection",
            "general.publish_to_foreign_groups_graph_collection",
            "general.publish_to_groups_graph_collection",
            "general.publish_graph_tuning",
            "general.publish_to_foreign_groups_graph_tuning",
            "general.publish_to_groups_graph_tuning",
            "general.publish_reports",
            "general.publish_reports_to_foreign_groups",
            "general.publish_reports_to_groups",
            "general.publish_sla_configuration",
            "general.publish_to_foreign_groups_sla_configuration",
            "general.publish_to_groups_sla_configuration",
            "general.publish_stored_report",
            "general.publish_to_foreign_groups_forecast_graph",
            "general.publish_to_groups_forecast_graph",
            "general.see_user_custom_graph",
            "general.see_user_forecast_graph",
            "general.see_user_graph_collection",
            "general.see_user_graph_tuning",
            "general.see_user_reports",
            "general.see_user_sla_configuration",
            "general.see_user_stored_report",
            "general.reporting",
            "general.schedule_reports",
            "general.schedule_reports_all",
            "general.force_forecast_graph",
            "general.force_reports",
            "general.force_sla_configuration",
            "general.instant_reports",
            "general.publish_custom_graph",
            "general.publish_to_foreign_groups_custom_graph",
            "general.publish_to_groups_custom_graph",
            "icons_and_actions.deployment_status",
            "icons_and_actions.ntop_host",
        ]

    if cmk_version.is_managed_edition():
        expected_permissions += [
            "wato.customer_management",
            "view.customers",
            "view.customer_hosts",
            "view.customer_hosts_up",
            "view.customer_hosts_down",
            "view.customer_hosts_pend",
            "view.customer_hosts_unreach",
            "sidesnap.customers",
        ]

    assert sorted(expected_permissions) == sorted(permission_registry.keys())

    for perm in permission_registry.values():
        assert isinstance(perm.description, (str, LazyString))
        assert isinstance(perm.title, (str, LazyString))
        assert isinstance(perm.defaults, list)


def test_declare_permission_section(monkeypatch):
    monkeypatch.setattr(
        permissions, "permission_section_registry", permissions.PermissionSectionRegistry()
    )
    assert "bla" not in permissions.permission_section_registry
    cmk.gui.config.declare_permission_section("bla", "bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    section = permissions.permission_section_registry["bla"]()
    assert section.title == "bla perm"
    assert section.sort_index == 50
    assert section.do_sort is False


def test_declare_permission(monkeypatch):
    monkeypatch.setattr(
        permissions, "permission_section_registry", permissions.PermissionSectionRegistry()
    )
    assert "bla" not in permissions.permission_section_registry
    cmk.gui.config.declare_permission_section("bla", "bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    monkeypatch.setattr(permissions, "permission_registry", permissions.PermissionRegistry())
    assert "bla.blub" not in permissions.permission_registry
    cmk.gui.config.declare_permission("bla.blub", "bla perm", "descrrrrr", ["admin"])
    assert "bla.blub" in permissions.permission_registry

    permission = permissions.permission_registry["bla.blub"]
    assert permission.section == permissions.permission_section_registry["bla"]
    assert permission.name == "bla.blub"
    assert permission.title == "bla perm"
    assert permission.description == "descrrrrr"
    assert permission.defaults == ["admin"]


@pytest.mark.parametrize(
    "do_sort,result",
    [
        (True, ["sec1.1", "sec1.A", "sec1.a", "sec1.b", "sec1.g", "sec1.Z", "sec1.z"]),
        (False, ["sec1.Z", "sec1.z", "sec1.A", "sec1.b", "sec1.a", "sec1.1", "sec1.g"]),
    ],
)
def test_permission_sorting(do_sort, result):
    sections = permissions.PermissionSectionRegistry()
    perms = permissions.PermissionRegistry()

    @sections.register
    class Sec1(permissions.PermissionSection):
        @property
        def name(self):
            return "sec1"

        @property
        def title(self):
            return "SEC1"

        @property
        def do_sort(self):
            return do_sort

    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        perms.register(
            Permission(
                section=Sec1,
                name=permission_name,
                title=permission_name.title(),
                description="bla",
                defaults=["admin"],
            )
        )

    sorted_perms = [p.name for p in perms.get_sorted_permissions(Sec1())]
    assert sorted_perms == result


@pytest.mark.parametrize(
    "site,result",
    [
        # Possible formats pre 1.6:
        (
            {},
            {
                "socket": ("local", None),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {
                "socket": None,
            },
            {
                "socket": ("local", None),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {"socket": "disabled"},
            {
                "socket": ("local", None),
                "disabled": True,
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {"socket": "unix:/ab:c/xyz"},
            {
                "socket": ("unix", {"path": "/ab:c/xyz"}),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {"socket": "tcp:127.0.0.1:1234"},
            {
                "socket": (
                    "tcp",
                    {
                        "address": ("127.0.0.1", 1234),
                        "tls": ("plain_text", {}),
                    },
                ),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {"socket": "tcp6:::1:1234"},
            {
                "socket": (
                    "tcp6",
                    {
                        "address": ("::1", 1234),
                        "tls": ("plain_text", {}),
                    },
                ),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {
                "socket": (
                    "proxy",
                    {
                        "socket": None,
                    },
                )
            },
            {
                "socket": ("local", None),
                "proxy": {},
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {
                "socket": (
                    "proxy",
                    {
                        "socket": ("127.0.0.1", 6790),
                    },
                )
            },
            {
                "socket": (
                    "tcp",
                    {
                        "address": ("127.0.0.1", 6790),
                        "tls": ("plain_text", {}),
                    },
                ),
                "proxy": {},
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        # Is allowed in 1.6 and should not be converted
        (
            {"proxy": {}, "socket": ("unix", {"path": "/a/b/c"})},
            {
                "socket": ("unix", {"path": "/a/b/c"}),
                "proxy": {},
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {
                "socket": (
                    "tcp",
                    {
                        "address": ("127.0.0.1", 1234),
                        "tls": ("plain_text", {}),
                    },
                )
            },
            {
                "socket": (
                    "tcp",
                    {
                        "address": ("127.0.0.1", 1234),
                        "tls": ("plain_text", {}),
                    },
                ),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {
                "socket": (
                    "tcp6",
                    {
                        "address": ("::1", 1234),
                        "tls": ("plain_text", {}),
                    },
                ),
            },
            {
                "socket": (
                    "tcp6",
                    {
                        "address": ("::1", 1234),
                        "tls": ("plain_text", {}),
                    },
                ),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {"socket": ("local", None)},
            {
                "socket": ("local", None),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
        (
            {"socket": ("unix", {"path": "/a/b/c"})},
            {
                "socket": ("unix", {"path": "/a/b/c"}),
                "proxy": None,
                "replication": None,
                "url_prefix": "/mysite/",
            },
        ),
    ],
)
def test_migrate_old_site_config(site, result):
    assert cmk.gui.config.prepare_raw_site_config(SiteConfigurations({SiteId("mysite"): site})) == {
        "mysite": result
    }


@pytest.mark.usefixtures("load_config")
def test_default_tags():
    groups = {
        "snmp_ds": [
            "no-snmp",
            "snmp-v1",
            "snmp-v2",
        ],
        "address_family": [
            "ip-v4-only",
            "ip-v4v6",
            "ip-v6-only",
            "no-ip",
        ],
        "piggyback": [
            "auto-piggyback",
            "piggyback",
            "no-piggyback",
        ],
        "agent": [
            "all-agents",
            "cmk-agent",
            "no-agent",
            "special-agents",
        ],
    }

    assert sorted(dict(config.tags.get_tag_group_choices()).keys()) == sorted(groups.keys())

    for tag_group in config.tags.tag_groups:
        assert sorted(tag_group.get_tag_ids(), key=lambda s: s or "") == sorted(
            groups[tag_group.id]
        )


@pytest.mark.usefixtures("load_config")
def test_default_aux_tags():
    assert sorted(config.tags.aux_tag_list.get_tag_ids()) == sorted(
        [
            "checkmk-agent",
            "ip-v4",
            "ip-v6",
            "ping",
            "snmp",
            "tcp",
        ]
    )
