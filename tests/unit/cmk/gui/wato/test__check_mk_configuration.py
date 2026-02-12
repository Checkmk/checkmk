#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from unittest.mock import patch

import pytest

from cmk.gui.wato._check_mk_configuration import (
    _migrate_piggybacked_host_files,
    ConfigVariableUseNewDescriptionsFor,
    migrate_snmp_fetch_interval,
)
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING


def test_migrate_snmp_fetch_interval_single() -> None:
    assert migrate_snmp_fetch_interval(("foo.bar", 42)) == (["foo"], ("cached", 42.0 * 60.0))
    assert migrate_snmp_fetch_interval(migrate_snmp_fetch_interval(("foo.bar", 42))) == (
        ["foo"],
        ("cached", 42.0 * 60.0),
    )


def test_migrate_snmp_fetch_interval_all() -> None:
    with patch(
        "cmk.gui.wato._check_mk_configuration.get_snmp_section_names",
        return_value=[("foo", "foo"), ("bar", "bar")],
    ):
        assert migrate_snmp_fetch_interval((None, 3)) == (["foo", "bar"], ("cached", 3.0 * 60.0))
        assert migrate_snmp_fetch_interval(migrate_snmp_fetch_interval((None, 3))) == (
            ["foo", "bar"],
            ("cached", 3.0 * 60.0),
        )


def test_migrate_snmp_fetch_interval_already_migrated_single_cached() -> None:
    new = (["foo"], ("cached", 42.0 * 60.0))
    assert migrate_snmp_fetch_interval(new) == new


def test_migrate_snmp_fetch_interval_already_migrated_single_uncached() -> None:
    new = (["foo"], ("uncached", None))
    assert migrate_snmp_fetch_interval(new) == new


def test_migrate_snmp_fetch_interval_all_already_migrate_cached() -> None:
    new = (["foo", "bar"], ("cached", 3.0 * 60.0))
    with patch(
        "cmk.gui.wato._check_mk_configuration.get_snmp_section_names",
        return_value=[("foo", "foo"), ("bar", "bar")],
    ):
        assert migrate_snmp_fetch_interval(new) == new


def test_migrate_snmp_fetch_interval_all_already_migrate_uncached() -> None:
    new = (["foo", "bar"], ("uncached", None))
    with patch(
        "cmk.gui.wato._check_mk_configuration.get_snmp_section_names",
        return_value=[("foo", "foo"), ("bar", "bar")],
    ):
        assert migrate_snmp_fetch_interval(new) == new


@pytest.mark.parametrize(
    ("rule_value", "expected_result"),
    [
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [
                            ("exact_match", "some-host"),
                            ("regular_expression", "test.*"),
                        ],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [
                            ("exact_match", "some-host"),
                            ("regular_expression", "test.*"),
                        ],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="up-to-date format",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["valid"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [("exact_match", "valid")],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="legacy format with valid host name",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["~test.*"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [("regular_expression", "test.*")],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="legacy format with regular expression",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["^test$", "^test2.*"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    }
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [],
            },
            id="legacy format with invalid host names",
        ),
    ],
)
def test_migrate_piggybacked_host_files(
    rule_value: Mapping[str, object],
    expected_result: Mapping[str, object],
) -> None:
    assert _migrate_piggybacked_host_files(rule_value) == expected_result


_AVAIL_PLUGIN_SELECTION_PRE_DATA_FORMAT_MIGRATION = frozenset(
    [
        "aix_memory",
        "barracuda_mailqueues",
        "brocade_sys_mem",
        "casa_cpu_temp",
        "cisco_mem",
        "cisco_mem_asa",
        "cisco_mem_asa64",
        "cmciii_psm_current",
        "cmciii_temp",
        "cmciii_lcp_airin",
        "cmciii_lcp_airout",
        "cmciii_lcp_water",
        "cmk_inventory",
        "db2_mem",
        "df",
        "df_netapp",
        "df_netapp32",
        "docker_container_mem",
        "enterasys_temp",
        "esx_vsphere_datastores",
        "esx_vsphere_hostsystem_mem_usage",
        "esx_vsphere_hostsystem_mem_usage_cluster",
        "etherbox_temp",
        "fortigate_memory",
        "fortigate_memory_base",
        "fortigate_node_memory",
        "hr_fs",
        "hr_mem",
        "http",
        "huawei_switch_mem",
        "hyperv_vms",
        "ibm_svc_mdiskgrp",
        "ibm_svc_system",
        "ibm_svc_systemstats_cache",
        "ibm_svc_systemstats_disk_latency",
        "ibm_svc_systemstats_diskio",
        "ibm_svc_systemstats_iops",
        "innovaphone_mem",
        "innovaphone_temp",
        "juniper_mem",
        "juniper_screenos_mem",
        "juniper_trpz_mem",
        "liebert_bat_temp",
        "logwatch",
        "logwatch_groups",
        "mem_used",
        "mem_win",
        "megaraid_bbu",
        "megaraid_pdisks",
        "megaraid_ldisks",
        "megaraid_vdisks",
        "mknotifyd",
        "mknotifyd_connection",
        "mssql_backup",
        "mssql_blocked_sessions",
        "mssql_counters_cache_hits",
        "mssql_counters_file_sizes",
        "mssql_counters_locks",
        "mssql_counters_locks_per_batch",
        "mssql_counters_pageactivity",
        "mssql_counters_sqlstats",
        "mssql_counters_transactions",
        "mssql_databases",
        "mssql_datafiles",
        "mssql_tablespaces",
        "mssql_transactionlogs",
        "mssql_versions",
        "netscaler_mem",
        "nullmailer_mailq",
        "prism_alerts",
        "prism_containers",
        "prism_info",
        "prism_storage_pools",
        "nvidia_temp",
        "postfix_mailq",
        "ps",
        "qmail_stats",
        "raritan_emx",
        "raritan_pdu_inlet",
        "services",
        "solaris_mem",
        "sophos_memory",
        "statgrab_mem",
        "tplink_mem",
        "ups_bat_temp",
        "vms_diskstat_df",
        "wmic_process",
        "zfsget",
    ]
)

# TODO: Was in the sample config, but not available for selection in the UI
# Excluded for now to test the status-quo, but needs to be investigated if it needs be added
# to the selection
_KNOWN_EXCEPTIONS = frozenset(["megaraid_vdisks"])


@pytest.mark.parametrize(
    "selected_plugins",
    [
        pytest.param(
            list(_AVAIL_PLUGIN_SELECTION_PRE_DATA_FORMAT_MIGRATION), id="full default selection"
        ),
        pytest.param(["df", "ps", "logwatch"], id="partial selection"),
        pytest.param([], id="empty list"),
    ],
)
def test_migrate_use_new_descriptions_for_from_list(selected_plugins: list[str]) -> None:
    value_spec = ConfigVariableUseNewDescriptionsFor().valuespec()
    migrated_selection = value_spec.transform_value(selected_plugins)

    assert isinstance(migrated_selection, dict)

    value_spec.validate_value(migrated_selection, "")
    value_spec.validate_datatype(migrated_selection, "")

    for selected_plugin in set(selected_plugins) - _KNOWN_EXCEPTIONS:
        assert migrated_selection[selected_plugin]

    for plugin_name in (
        _AVAIL_PLUGIN_SELECTION_PRE_DATA_FORMAT_MIGRATION
        - set(selected_plugins)
        - _KNOWN_EXCEPTIONS
    ):
        assert not migrated_selection[plugin_name]


def test_migrate_use_new_descriptions_for_from_sample_config() -> None:
    value_spec = ConfigVariableUseNewDescriptionsFor().valuespec()

    migrated_default_selection = value_spec.transform_value(
        USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"]
    )

    assert isinstance(migrated_default_selection, dict)

    value_spec.validate_value(migrated_default_selection, "")
    value_spec.validate_datatype(migrated_default_selection, "")

    for plugin_name, expected_selected in USE_NEW_DESCRIPTIONS_FOR_SETTING[
        "use_new_descriptions_for"
    ].items():
        if plugin_name in _KNOWN_EXCEPTIONS:
            continue
        assert migrated_default_selection[plugin_name] == expected_selected


def test_migrate_use_new_descriptions_for_new_choices_auto_enabled() -> None:
    use_new_descriptions_for_new_choices_missing = {"df": False, "ps": False, "logwatch": False}
    value_spec = ConfigVariableUseNewDescriptionsFor().valuespec()

    migrated_selection = value_spec.transform_value(use_new_descriptions_for_new_choices_missing)

    assert isinstance(migrated_selection, dict)

    value_spec.validate_value(migrated_selection, "")
    value_spec.validate_datatype(migrated_selection, "")

    # new choices are added and enabled
    assert len(migrated_selection) > len(use_new_descriptions_for_new_choices_missing)
    for plugin_name, is_selected in migrated_selection.items():
        assert use_new_descriptions_for_new_choices_missing.get(plugin_name, True) == is_selected


def test_migrate_vanished_option() -> None:
    use_new_descriptions_for_vanished_option = {"i_can_longer_be_selected": True}
    value_spec = ConfigVariableUseNewDescriptionsFor().valuespec()

    migrated_selection = value_spec.transform_value(use_new_descriptions_for_vanished_option)

    assert isinstance(migrated_selection, dict)
    value_spec.validate_value(migrated_selection, "")
    value_spec.validate_datatype(migrated_selection, "")

    assert "i_can_longer_be_selected" not in migrated_selection
