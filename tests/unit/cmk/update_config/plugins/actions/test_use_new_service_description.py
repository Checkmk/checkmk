#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Generator, Sequence
from contextlib import contextmanager

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import Item

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, AutochecksStore

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING

from cmk.update_config.plugins.actions.use_new_service_description import (
    UpdateUseNewServiceDescription,
)

_USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS = USE_NEW_DESCRIPTIONS_FOR_SETTING[
    "use_new_descriptions_for"
]


@contextmanager
def _setup_autochecks(autochecks_setup: Sequence[tuple[CheckPluginName, Item]]) -> Generator[None]:
    host_name = "test_host"
    store = AutochecksStore(HostName(host_name))
    original_entries = store.read()
    try:
        entries = []
        for plugin_name, item in autochecks_setup:
            entry = AutocheckEntry(
                check_plugin_name=plugin_name, item=item, parameters={}, service_labels={}
            )
            entries.append(entry)
        store.write(entries)
        yield
    finally:
        store.write(original_entries)


@contextmanager
def _setup_global_settings(global_settings_setup: GlobalSettings) -> Generator[None]:
    original_global_settings = load_configuration_settings(full_config=True)
    try:
        save_global_settings(global_settings_setup)
        yield
    finally:
        save_global_settings(original_global_settings)


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    ["initial_global_settings", "expected_global_settings"],
    [
        pytest.param(
            {
                "use_new_descriptions_for": {
                    plugin: True
                    for plugin in set(_USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS) - {"casa_cpu_temp"}
                }
            },
            {
                "use_new_descriptions_for": {
                    plugin: plugin != "casa_cpu_temp"
                    for plugin in _USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS
                }
            },
            id="new_plugin_added_is_disabled",
        ),
        pytest.param(
            {
                "use_new_descriptions_for": {
                    plugin: True
                    for plugin in set(_USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS) - {"casa_cpu_temp"}
                }
                | {"casa_cpu_temp": False}
            },
            {
                "use_new_descriptions_for": {
                    plugin: plugin != "casa_cpu_temp"
                    for plugin in _USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS
                }
            },
            id="disabled_plugin_stays_disabled",
        ),
        pytest.param(
            {
                "use_new_descriptions_for": {
                    plugin: False
                    for plugin in set(_USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS) - {"casa_cpu_temp"}
                }
                | {"casa_cpu_temp": True}
            },
            {
                "use_new_descriptions_for": {
                    plugin: plugin in ("casa_cpu_temp",)
                    for plugin in _USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS
                }
            },
            id="enabled_plugin_stays_enabled",
        ),
    ],
)
def test_update_action_new_format(
    initial_global_settings: GlobalSettings,
    expected_global_settings: GlobalSettings,
) -> None:
    with _setup_global_settings(initial_global_settings):
        action = UpdateUseNewServiceDescription(
            name="use_new_service_description",
            title="Use new service description",
            sort_index=17,  # before rulesets and global settings
        )
        action(logging.getLogger())

        global_settings = load_configuration_settings(full_config=True)
        assert (
            global_settings["use_new_descriptions_for"]
            == expected_global_settings["use_new_descriptions_for"]
        )


@pytest.mark.usefixtures("request_context")
def test_update_action_raises_on_removed_plugin() -> None:
    initial_global_settings: GlobalSettings = {
        "use_new_descriptions_for": {
            plugin: True for plugin in _USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS
        }
        | {"removed_plugin": True}
    }
    with _setup_autochecks([]), _setup_global_settings(initial_global_settings):
        action = UpdateUseNewServiceDescription(
            name="use_new_service_description",
            title="Use new service description",
            sort_index=17,  # before rulesets and global settings
        )
        with pytest.raises(
            NotImplementedError,
            match="Removing plugins from 'use_new_descriptions_for' is not possible at the moment. The following plugins where found in the configuration under update, but are not configurable in the new Checkmk version: {'removed_plugin'}",
        ):
            action(logging.getLogger())


_PRE_DATA_FORMAT_MIGRATION_SAMPLE_CONFIG = [
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


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    ["initial_global_settings", "expected_global_settings"],
    [
        pytest.param(
            {"use_new_descriptions_for": _PRE_DATA_FORMAT_MIGRATION_SAMPLE_CONFIG},
            {
                "use_new_descriptions_for": {
                    plugin: True for plugin in _USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS
                }
            },
            id="all_plugins_enabled_migrated",
        ),
        pytest.param(
            {"use_new_descriptions_for": []},
            {
                "use_new_descriptions_for": {
                    plugin: False for plugin in _USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS
                }
            },
            id="descriptions_prev_disabled_stay_disabled",
        ),
        pytest.param(
            {"use_new_descriptions_for": ["cmciii_temp"]},
            {
                "use_new_descriptions_for": {
                    plugin: False
                    for plugin in set(_USE_NEW_DESCRIPTIONS_FOR_SETTING_PLUGINS) - {"cmciii_temp"}
                }
                | {
                    "cmciii_temp": True,
                }
            },
            id="descriptions_prev_enabled_stay_enabled",
        ),
    ],
)
def test_update_action_from_old_format(
    initial_global_settings: GlobalSettings,
    expected_global_settings: GlobalSettings,
) -> None:
    with _setup_global_settings(initial_global_settings):
        action = UpdateUseNewServiceDescription(
            name="use_new_service_description",
            title="Use new service description",
            sort_index=17,  # before rulesets and global settings
        )
        action(logging.getLogger())

        global_settings = load_configuration_settings(full_config=True)
        assert (
            global_settings["use_new_descriptions_for"]
            == expected_global_settings["use_new_descriptions_for"]
        )
