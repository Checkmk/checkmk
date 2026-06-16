#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.gui.watolib.automation_commands import automation_command_registry
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    configvar_order,
)


def test_registered_config_domains() -> None:
    expected_config_domains = [
        "apache",
        "ca-certificates",
        "check_mk",
        "diskspace",
        "ec",
        "multisite",
        "omd",
        "rrdcached",
        "site-certificate",
        "product_usage_analytics",
        "release_flags",
    ]

    registered = sorted(config_domain_registry.keys())
    assert registered == sorted(expected_config_domains)


def test_registered_automation_commands() -> None:
    expected_automation_commands = [
        "activate-changes",
        "agent-download-token-create",
        "agent-registration-token-create",
        "check-analyze-config",
        "checkmk-remote-automation-get-status",
        "checkmk-remote-automation-start",
        "clear-site-changes",
        "create-broker-certs",
        "diagnostics-dump-get-file",
        "diagnostics-dump-os-walk",
        "discovered-host-label-sync",
        "fetch-agent-output-get-file",
        "fetch-agent-output-get-status",
        "fetch-agent-output-start",
        "fetch-background-job-snapshot",
        "fetch-quick-setup-stage-action-result",
        "finalize-site-ca-certificate-rotation",
        "get-agent-receiver-port",
        "get-config-sync-state",
        "hosts-for-auto-removal",
        "network-scan",
        "notification-test",
        "ping",
        "push-profiles",
        "receive-config-sync",
        "remove-tls-registration",
        "rename-hosts-uuid-link",
        "service-discovery-job",
        "service-discovery-job-snapshot",
        "site-certificate-rotation",
        "stage-site-ca-certificate-rotation",
        "start-quick-setup-stage-action",
        "store-broker-certs",
        "sync-remote-site",
    ]

    registered = sorted(automation_command_registry.keys())
    assert registered == sorted(expected_automation_commands)


def test_registered_configvars() -> None:
    expected_vars = [
        "actions",
        "adhoc_downtime",
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
        "default_dynamic_visual_permission",
        "delay_precompile",
        "diskspace_cleanup",
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
        "sqlite_housekeeping_interval",
        "sqlite_freelist_size",
        "user_security_notification_duration",
        "http_proxies",
        "inventory_check_autotrigger",
        "inventory_check_interval",
        "inventory_check_severity",
        "inventory_cleanup",
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
        "require_two_factor_all_users",
        "reschedule_timeout",
        "snmp_walk_download_timeout",
        "restart_locking",
        "retention_interval",
        "rrdcached_tuning",
        "rule_optimizer",
        "selection_livetime",
        "service_view_grouping",
        "session_mgmt",
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
        "site_piggyback_hub",
        "site_subject_alternative_names",
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
        "use_new_descriptions_for",
        "user_downtime_timeranges",
        "user_icons_and_actions",
        "user_localizations",
        "acknowledge_problems",
        "virtual_host_trees",
        "wato_activation_method",
        "wato_activate_changes_comment_mode",
        "wato_hide_filenames",
        "wato_hide_folders_without_read_permissions",
        "wato_hide_hosttags",
        "wato_hide_varnames",
        "wato_icon_categories",
        "wato_max_snapshots",
        "wato_pprint_config",
        "wato_use_git",
        "graph_timeranges",
        "agent_controller_certificates",
        "rest_api_etag_locking",
        "enable_login_via_get",
        "enable_deprecated_automation_user_authentication",
        "default_language",
        "default_temperature_unit",
        "vue_experimental_features",
        "inject_js_profiling_code",
        "load_frontend_vue",
        "site_trace_send",
        "site_trace_receive",
        "product_usage_analytics",
    ]

    registered = sorted(config_variable_registry.keys())
    assert registered == sorted(expected_vars)


def test_registered_configvar_groups() -> None:
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
        "Developer Tools",
        "Product usage analytics",
    ]

    registered = sorted(config_variable_group_registry.keys())
    assert registered == sorted(expected_groups)


def test_legacy_configvar_order_access() -> None:
    with pytest.raises(NotImplementedError) as e:
        configvar_order()["x"] = 10
    assert "werk #6911" in "%s" % e


class _EvulToStr:
    def __str__(self):
        return "' boom!"
