#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"


from dataclasses import asdict

import pytest

import cmk.gui.config
import cmk.utils.paths
from cmk.gui.config import active_config, Config
from tests.testlib.common.repo import (
    is_pro_repo,
    is_ultimatemt_repo,
)


def test_default_config_from_plugins() -> None:
    expected = [
        "roles",
        "debug",
        "screenshotmode",
        "profile",
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
        "acknowledge_problems",
        "custom_links",
        "debug_livestatus_queries",
        "show_livestatus_errors",
        "liveproxyd_enabled",
        "service_view_grouping",
        "custom_style_sheet",
        "ui_theme",
        "show_mode",
        "start_url",
        "page_heading",
        "login_screen",
        "reschedule_timeout",
        "snmp_walk_download_timeout",
        "filter_columns",
        "default_language",
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
        "agent_controller_certificates",
        "userdb_automatic_sync",
        "user_login",
        "user_connections",
        "default_user_profile",
        "log_logon_failures",
        "lock_on_logon_failures",
        "single_user_session",
        "site_subject_alternative_names",
        "password_policy",
        "user_localizations",
        "user_icons_and_actions",
        "custom_service_attributes",
        "user_downtime_timeranges",
        "builtin_icon_visibility",
        "trusted_certificate_authorities",
        "user_security_notification_duration",
        "mkeventd_enabled",
        "mkeventd_pprint_rules",
        "mkeventd_notify_contactgroup",
        "mkeventd_notify_facility",
        "mkeventd_notify_remotehost",
        "mkeventd_connect_timeout",
        "log_level",
        "log_rulehits",
        "rule_optimizer",
        "session_mgmt",
        "mkeventd_service_levels",
        "wato_host_tags",
        "wato_aux_tags",
        "wato_tags",
        "wato_enabled",
        "wato_hide_filenames",
        "wato_hide_hosttags",
        "wato_hide_varnames",
        "wato_hide_help_in_lists",
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
        "broker_connections",
        "sites",
        "config_storage_format",
        "tags",
        "enable_login_via_get",
        "enable_deprecated_automation_user_authentication",
        "default_temperature_unit",
        "vue_experimental_features",
        "inject_js_profiling_code",
        "load_frontend_vue",
        "configuration_bundles",
        "default_dynamic_visual_permission",
        "require_two_factor_all_users",
        "inventory_cleanup",
    ]

    # The below lines are confusing and incorrect. The reason we need them is
    # because our test environments do not reflect our Checkmk editions properly.
    # We cannot fix that in the short (or even mid) term because the
    # precondition is a more cleanly separated structure.

    if is_pro_repo():
        # CEE plug-ins are added when the CEE plug-ins for WATO are available, i.e.
        # when the "enterprise/" path is present.
        expected += [
            "agent_deployment_enabled",
            "agent_deployment_host_selection",
            "agent_deployment_central",
            "agent_deployment_remote",
            "agent_signature_keys",
            "have_combined_graphs",
            "licensing_settings",
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

    if is_ultimatemt_repo():
        # CME plug-ins are added when the CEE plug-ins for WATO are available, i.e.
        # when the "managed/" path is present.
        expected += [
            "customers",
            "current_customer",
        ]

    default_config = cmk.gui.config.get_default_config()
    assert sorted(list(default_config.keys())) == sorted(expected)

    default_config2 = asdict(cmk.gui.config.make_config_object(default_config))
    assert sorted(default_config2.keys()) == sorted(expected)


def test_load_config(request_context: None) -> None:
    config_path = cmk.utils.paths.default_config_dir / "multisite.mk"
    config_path.unlink(missing_ok=True)

    config = cmk.gui.config.load_config()
    assert config.quicksearch_dropdown_limit == 80
    assert active_config.quicksearch_dropdown_limit == 80

    with config_path.open("w") as f:
        f.write("quicksearch_dropdown_limit = 1337\n")
    config = cmk.gui.config.load_config()
    assert config.quicksearch_dropdown_limit == 1337

    # load_config must not modify the active_config
    assert active_config.quicksearch_dropdown_limit == 80


@pytest.fixture()
def local_config_plugin():
    config_plugin = cmk.utils.paths.local_web_dir / "plugins" / "config" / "test.py"
    config_plugin.parent.mkdir(parents=True)
    with config_plugin.open("w") as f:
        f.write("ding = 'dong'\n")


@pytest.mark.usefixtures("local_config_plugin")
def test_load_config_respects_local_plugin(request_context: None) -> None:
    config = cmk.gui.config.load_config()
    assert config.ding == "dong"  # type: ignore[attr-defined, unused-ignore]


@pytest.mark.usefixtures("local_config_plugin")
def test_load_config_allows_local_plugin_setting(request_context: None) -> None:
    with (cmk.utils.paths.default_config_dir / "multisite.mk").open("w") as f:
        f.write("ding = 'ding'\n")
    config = cmk.gui.config.load_config()
    assert config.ding == "ding"  # type: ignore[attr-defined, unused-ignore]


def test_default_tags(load_config: Config) -> None:
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

    assert sorted(dict(load_config.tags.get_tag_group_choices()).keys()) == sorted(groups.keys())

    for tag_group in load_config.tags.tag_groups:
        assert sorted(tag_group.get_tag_ids(), key=lambda s: s or "") == sorted(
            groups[tag_group.id]
        )


def test_default_aux_tags(load_config: Config) -> None:
    assert sorted(load_config.tags.aux_tag_list.get_tag_ids()) == sorted(
        [
            "checkmk-agent",
            "ip-v4",
            "ip-v6",
            "ping",
            "snmp",
            "tcp",
        ]
    )


def test_config_initialize_updates_active_config(request_context: None) -> None:
    config_path = cmk.utils.paths.default_config_dir / "multisite.mk"

    assert active_config.quicksearch_dropdown_limit == 80

    config_path.write_text("quicksearch_dropdown_limit = 1337\n")
    config = cmk.gui.config.initialize()
    assert config.quicksearch_dropdown_limit == 1337
    assert active_config.quicksearch_dropdown_limit == 1337
