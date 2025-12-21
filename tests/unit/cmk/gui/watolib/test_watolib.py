#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest

import cmk.ccc.version as cmk_version
from cmk.gui.watolib.automation_commands import automation_command_registry
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    configvar_order,
)
from cmk.utils import paths


def test_registered_config_domains() -> None:
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
        "site-certificate",
        "telemetry",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected_config_domains += [
            "dcd",
            "mknotifyd",
        ]

    if cmk_version.edition(paths.omd_root) in {
        cmk_version.Edition.ULTIMATE,
        cmk_version.Edition.ULTIMATEMT,
    }:
        expected_config_domains += [
            "metric_backend",
            "otel_collector",
        ]

    registered = sorted(config_domain_registry.keys())
    assert registered == sorted(expected_config_domains)


def test_registered_automation_commands() -> None:
    expected_automation_commands = [
        "activate-changes",
        "check-analyze-config",
        "checkmk-remote-automation-get-status",
        "checkmk-remote-automation-start",
        "clear-site-changes",
        "create-broker-certs",
        "diagnostics-dump-get-file",
        "discovered-host-label-sync",
        "diagnostics-dump-os-walk",
        "fetch-agent-output-get-file",
        "fetch-agent-output-get-status",
        "fetch-agent-output-start",
        "fetch-background-job-snapshot",
        "fetch-quick-setup-stage-action-result",
        "finalize-certificate-rotation",
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
        "stage-certificate-rotation",
        "start-quick-setup-stage-action",
        "store-broker-certs",
        "sync-remote-site",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected_automation_commands += [
            "execute-dcd-command",
            "get-agent-requests",
            "update-agent-requests",
            "distribute-verification-response",
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
        "product_telemetry",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected_vars += [
            "agent_bakery_logging",
            "agent_deployment_enabled",
            "agent_deployment_host_selection",
            "agent_deployment_central",
            "agent_deployment_remote",
            "alert_handler_event_types",
            "alert_handler_timeout",
            "alert_logging",
            "bake_agents_on_restart",
            "apply_bake_revision",
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
            "cmc_max_response_size",
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
            "dcd_activate_changes_timeout",
            "dcd_bulk_discovery_timeout",
            "dcd_log_levels",
            "dcd_site_update_interval",
            "dcd_max_activation_delay",
            "dcd_max_hosts_per_bulk_discovery",
            "dcd_prevent_unwanted_notification",
            "liveproxyd_default_connection_params",
            "liveproxyd_log_levels",
            "notification_spooler_config",
            "notification_spooling",
            "max_long_output_size",
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

    if cmk_version.edition(paths.omd_root) in {
        cmk_version.Edition.ULTIMATE,
        cmk_version.Edition.ULTIMATEMT,
    }:
        expected_vars += [
            "metric_backend",
            "site_opentelemetry_collector",
            "site_opentelemetry_collector_memory_limit",
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
        "Product telemetry",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected_groups += [
            "Dynamic configuration",
            "Automatic agent updates",
            "Alert handlers",
            "Livestatus proxy",
            "Reporting",
            "Monitoring core",
            "Ntopng (chargeable add-on)",
            "Application Monitoring",
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
