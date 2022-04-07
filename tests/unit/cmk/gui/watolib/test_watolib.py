#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.version as cmk_version

import cmk.gui.watolib as watolib
from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    configvar_order,
    ConfigVariableGroup,
)
from cmk.gui.valuespec import ValueSpec


def test_registered_config_domains():
    expected_config_domains = [
        "apache",
        "ca-certificates",
        "check_mk",
        "diskspace",
        "ec",
        "liveproxyd",
        "multisite",
        "omd",
        "rrdcached",
    ]

    if not cmk_version.is_raw_edition():
        expected_config_domains += [
            "dcd",
            "mknotifyd",
        ]

    registered = sorted(watolib.config_domain_registry.keys())
    assert registered == sorted(expected_config_domains)


def test_registered_automation_commands():

    expected_automation_commands = [
        "activate-changes",
        "push-profiles",
        "check-analyze-config",
        "diagnostics-dump-get-file",
        "fetch-agent-output-get-file",
        "fetch-agent-output-get-status",
        "fetch-agent-output-start",
        "network-scan",
        "ping",
        "push-snapshot",
        "get-config-sync-state",
        "receive-config-sync",
        "service-discovery-job",
        "checkmk-remote-automation-start",
        "checkmk-remote-automation-get-status",
        "discovered-host-label-sync",
    ]

    if not cmk_version.is_raw_edition():
        expected_automation_commands += [
            "execute-dcd-command",
            "get-agent-requests",
            "update-agent-requests",
        ]

    registered = sorted(watolib.automation_command_registry.keys())
    assert registered == sorted(expected_automation_commands)


def test_registered_configvars():
    expected_vars = [
        "actions",
        "adhoc_downtime",
        "agent_simulator",
        "apache_process_tuning",
        "archive_orphans",
        "auth_by_http_header",
        "builtin_icon_visibility",
        "bulk_discovery_default_settings",
        "check_mk_perfdata_with_times",
        "cluster_max_cachefile_age",
        "crash_report_target",
        "crash_report_url",
        "custom_service_attributes",
        "debug",
        "debug_livestatus_queries",
        "debug_rules",
        "default_user_profile",
        "default_bi_layout",
        "delay_precompile",
        "diskspace_cleanup",
        "enable_rulebased_notifications",
        "enable_sounds",
        "escape_plugin_output",
        "event_limit",
        "eventsocket_queue_len",
        "failed_notification_horizon",
        "hard_query_limit",
        "history_lifetime",
        "history_rotation",
        "hostname_translation",
        "housekeeping_interval",
        "http_proxies",
        "inventory_check_autotrigger",
        "inventory_check_interval",
        "inventory_check_severity",
        "log_logon_failures",
        "lock_on_logon_failures",
        "log_level",
        "log_levels",
        "log_messages",
        "log_rulehits",
        "login_screen",
        "mkeventd_connect_timeout",
        "mkeventd_notify_contactgroup",
        "mkeventd_notify_facility",
        "mkeventd_notify_remotehost",
        "mkeventd_pprint_rules",
        "mkeventd_service_levels",
        "multisite_draw_ruleicon",
        "notification_backlog",
        "notification_bulk_interval",
        "notification_fallback_email",
        "notification_fallback_format",
        "notification_logging",
        "notification_plugin_timeout",
        "page_heading",
        "pagetitle_date_format",
        "password_policy",
        "piggyback_max_cachefile_age",
        "profile",
        "quicksearch_dropdown_limit",
        "quicksearch_search_order",
        "remote_status",
        "replication",
        "reschedule_timeout",
        "restart_locking",
        "retention_interval",
        "rrdcached_tuning",
        "rule_optimizer",
        "selection_livetime",
        "service_view_grouping",
        "show_livestatus_errors",
        "show_mode",
        "sidebar_notify_interval",
        "sidebar_update_interval",
        "simulation_mode",
        "single_user_session",
        "site_autostart",
        "site_core",
        "site_livestatus_tcp",
        "site_mkeventd",
        "slow_views_duration_threshold",
        "snmp_credentials",
        "socket_queue_len",
        "soft_query_limit",
        "staleness_threshold",
        "start_url",
        "statistics_interval",
        "table_row_limit",
        "tcp_connect_timeout",
        "translate_snmptraps",
        "trusted_certificate_authorities",
        "ui_theme",
        "use_dns_cache",
        "snmp_backend_default",
        "use_inline_snmp",
        "use_new_descriptions_for",
        "user_downtime_timeranges",
        "user_icons_and_actions",
        "user_idle_timeout",
        "user_localizations",
        "view_action_defaults",
        "virtual_host_trees",
        "wato_activation_method",
        "wato_activate_changes_concurrency",
        "wato_activate_changes_comment_mode",
        "wato_hide_filenames",
        "wato_hide_folders_without_read_permissions",
        "wato_hide_help_in_lists",
        "wato_hide_hosttags",
        "wato_hide_varnames",
        "wato_icon_categories",
        "wato_max_snapshots",
        "wato_pprint_config",
        "wato_upload_insecure_snapshots",
        "wato_use_git",
        "graph_timeranges",
        "rest_api_etag_locking",
    ]

    if not cmk_version.is_raw_edition():
        expected_vars += [
            "agent_deployment_enabled",
            "agent_deployment_host_selection",
            "agent_deployment_central",
            "agent_deployment_remote",
            "alert_handler_event_types",
            "alert_handler_timeout",
            "alert_logging",
            "bake_agents_on_restart",
            "cmc_authorization",
            "cmc_check_helpers",
            "cmc_check_timeout",
            "cmc_config_multiprocessing",
            "cmc_debug_notifications",
            "cmc_dump_core",
            "cmc_fetcher_helpers",
            "cmc_checker_helpers",
            "cmc_flap_settings",
            "cmc_graphite",
            "cmc_import_nagios_state",
            "cmc_initial_scheduling",
            "cmc_livestatus_lines_per_file",
            "cmc_livestatus_logcache_size",
            "cmc_livestatus_threads",
            "cmc_log_cmk_helpers",
            "cmc_log_levels",
            "cmc_log_limit",
            "cmc_log_microtime",
            "cmc_log_rotation_method",
            "cmc_log_rrdcreation",
            "cmc_pnp_update_delay",
            "cmc_pnp_update_on_restart",
            "cmc_real_time_checks",
            "cmc_real_time_helpers",
            "cmc_smartping_tuning",
            "cmc_state_retention_interval",
            "cmc_statehist_cache",
            "cmc_timeperiod_horizon",
            "dcd_log_levels",
            "dcd_web_api_connection",
            "liveproxyd_default_connection_params",
            "liveproxyd_log_levels",
            "notification_spooler_config",
            "notification_spooling",
            "reporting_date_format",
            "reporting_email_options",
            "reporting_filename",
            "reporting_font_family",
            "reporting_font_size",
            "reporting_graph_layout",
            "reporting_lineheight",
            "reporting_margins",
            "reporting_mirror_margins",
            "reporting_pagesize",
            "reporting_rangespec",
            "reporting_table_layout",
            "reporting_time_format",
            "reporting_use",
            "reporting_view_limit",
            "site_liveproxyd",
            "ntop_connection",
        ]

    registered = sorted(config_variable_registry.keys())
    assert registered == sorted(expected_vars)


# Can be removed once we use mypy there
def test_registered_configvars_types():
    for var_class in config_variable_registry.values():
        var = var_class()
        assert issubclass(var.group(), ConfigVariableGroup)
        assert issubclass(var.domain(), ABCConfigDomain)
        assert isinstance(var.ident(), str)
        assert isinstance(var.valuespec(), ValueSpec)


def test_registered_configvar_groups():
    expected_groups = [
        "Setup",
        "Event Console: Generic",
        "Event Console: Logging & diagnose",
        "Event Console: SNMP traps",
        "Execution of checks",
        "Notifications",
        "Service discovery",
        "Site management",
        "User interface",
        "User management",
        "Support",
    ]

    if not cmk_version.is_raw_edition():
        expected_groups += [
            "Dynamic configuration",
            "Automatic agent updates",
            "Alert handlers",
            "Livestatus proxy",
            "Reporting",
            "Monitoring core",
            "Ntopng (chargeable add-on)",
        ]

    registered = sorted(config_variable_group_registry.keys())
    assert registered == sorted(expected_groups)


def test_legacy_configvar_order_access():
    with pytest.raises(NotImplementedError) as e:
        configvar_order()["x"] = 10
    assert "werk #6911" in "%s" % e
