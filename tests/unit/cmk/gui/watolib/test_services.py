#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator, Mapping
from unittest.mock import call, MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import HostLabel
from cmk.utils.sectionname import SectionName
from cmk.utils.servicename import ServiceName
from cmk.utils.user import UserId

from cmk.automations.results import (
    DeleteHostsResult,
    ServiceDiscoveryPreviewResult,
    SetAutochecksInput,
    SetAutochecksV2Result,
)

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, CheckPreviewEntry

from cmk.gui.utils import transaction_manager
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host
from cmk.gui.watolib.services import (
    DiscoveryAction,
    DiscoveryResult,
    get_check_table,
    initial_discovery_result,
    perform_fix_all,
    perform_host_label_discovery,
    perform_service_discovery,
)

MOCK_DISCOVERY_RESULT = ServiceDiscoveryPreviewResult(
    check_table=[
        CheckPreviewEntry(
            "unchanged",
            "cpu.loads",
            "cpu_load",
            None,
            None,
            {},
            {},
            {"levels": (5.0, 10.0)},
            "CPU load",
            0,
            "15 min load: 1.32 at 8 Cores (0.17 per Core)",
            [
                ("load1", 2.7, 40.0, 80.0, 0, 8),
                ("load5", 1.63, 40.0, 80.0, 0, 8),
                ("load15", 1.32, 40.0, 80.0, 0, 8),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "active",
            "cmk_inv",
            None,
            None,
            "Check_MK HW/SW Inventory",
            {},
            {},
            {},
            "Check_MK HW/SW Inventory",
            None,
            "WAITING - Active check, cannot be done offline",
            [],
            {},
            {},
            [HostName("heute")],
        ),
    ],
    nodes_check_table={},
    host_labels={"cmk/check_mk_server": {"plugin_name": "labels", "value": "yes"}},
    output="output",
    new_labels={},
    vanished_labels={},
    changed_labels={},
    source_results={"agent": (0, "Success")},
    labels_by_host={
        HostName("heute"): [HostLabel("cmk/check_mk_server", "yes", SectionName("labels"))]
    },
)


@pytest.fixture(name="mock_discovery_preview")
def fixture_mock_discovery_preview(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview", return_value=MOCK_DISCOVERY_RESULT
    )


@pytest.fixture(name="mock_discovery")
def fixture_mock_discovery(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("cmk.gui.watolib.services.local_discovery")


@pytest.fixture(name="mock_set_autochecks")
def fixture_mock_set_autochecks(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.services.set_autochecks_v2", return_value=SetAutochecksV2Result()
    )


@pytest.fixture(name="mock_add_service_change")
def mock_add_service_change(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("cmk.gui.watolib.changes.add_service_change", return_value=None)


@pytest.fixture(name="mock_check_transaction")
def fixture_check_transaction():
    return patch.object(
        transaction_manager.TransactionManager, "check_transaction", MagicMock(side_effect=[True])
    )


@pytest.fixture(name="sample_host_name")
def fixture_sample_host_name() -> HostName:
    return HostName("heute")


@pytest.fixture(name="sample_host")
def fixture_sample_host(
    request_context: None,
    with_admin_login: UserId,
    sample_host_name: HostName,
) -> Generator[Host, None, None]:
    hostname = sample_host_name
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts([(hostname, {}, None)])
    host = root_folder.host(hostname)
    assert host is not None
    yield host
    root_folder.delete_hosts([hostname], automation=lambda *args, **kwargs: DeleteHostsResult())


@pytest.mark.usefixtures("inline_background_jobs")
def test_perform_discovery_none_action(
    sample_host: Host, mock_discovery_preview: MagicMock
) -> None:
    discovery_result = initial_discovery_result(
        action=DiscoveryAction.NONE,
        host=sample_host,
        previous_discovery_result=None,
        raise_errors=True,
    )
    mock_discovery_preview.assert_called_once()
    assert discovery_result.check_table == MOCK_DISCOVERY_RESULT.check_table


@pytest.mark.usefixtures("inline_background_jobs")
def test_perform_discovery_tabula_rasa_action_with_no_previous_discovery_result(
    sample_host_name: HostName,
    sample_host: Host,
    mock_discovery_preview: MagicMock,
    mock_discovery: MagicMock,
) -> None:
    discovery_result = get_check_table(
        sample_host,
        DiscoveryAction.TABULA_RASA,
        raise_errors=True,
    )

    mock_discovery.assert_called_once()
    mock_discovery_preview.assert_has_calls(
        [
            call(sample_host_name, prevent_fetching=False, raise_errors=False),
        ]
    )
    assert discovery_result.check_table == MOCK_DISCOVERY_RESULT.check_table


@pytest.mark.usefixtures("inline_background_jobs")
def test_perform_discovery_fix_all_with_previous_discovery_result(
    mocker: MockerFixture,
    sample_host_name: HostName,
    sample_host: Host,
    mock_set_autochecks: MagicMock,
) -> None:
    mocker.patch("cmk.gui.watolib.services.update_host_labels", return_value={})
    mock_discovery_preview = mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview",
        return_value=ServiceDiscoveryPreviewResult(
            output="",
            check_table=[
                CheckPreviewEntry(
                    check_source="unchanged",
                    check_plugin_name="lnx_thermal",
                    ruleset_name="temperature",
                    discovery_ruleset_name=None,
                    item="Zone 1",
                    old_discovered_parameters={},
                    new_discovered_parameters={},
                    effective_parameters={
                        "levels": (70.0, 80.0),
                        "device_levels_handling": "devdefault",
                    },
                    description="Temperature Zone 1",
                    state=0,
                    output="Temperature: 43.0°C\nTemperature: 43.0°C\nConfiguration: prefer device levels over user levels (used device levels)",
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[sample_host_name],
                ),
                CheckPreviewEntry(
                    check_source="active",
                    check_plugin_name="cmk_inv",
                    ruleset_name=None,
                    discovery_ruleset_name=None,
                    item="Check_MK HW/SW Inventory",
                    old_discovered_parameters={},
                    new_discovered_parameters={},
                    effective_parameters={"status_data_inventory": True},
                    description="Check_MK HW/SW Inventory",
                    state=None,
                    output="WAITING - Active check, cannot be done offline",
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[sample_host_name],
                ),
            ],
            nodes_check_table={},
            host_labels={
                "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
                "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
            },
            new_labels={},
            vanished_labels={},
            changed_labels={},
            source_results={"agent": (0, "Success")},
            labels_by_host={
                sample_host_name: [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
                    HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
                ],
            },
        ),
    )
    previous_discovery_result = DiscoveryResult(
        job_status={
            "state": "initialized",
            "started": 1654006465.892057,
            "pid": None,
            "loginfo": {"JobProgressUpdate": [], "JobResult": [], "JobException": []},
            "is_active": False,
        },
        check_table_created=1654006465,
        check_table=[
            CheckPreviewEntry(
                check_source="new",
                check_plugin_name="lnx_thermal",
                ruleset_name="temperature",
                discovery_ruleset_name=None,
                item="Zone 1",
                old_discovered_parameters={},
                new_discovered_parameters={},
                effective_parameters={
                    "levels": (70.0, 80.0),
                    "device_levels_handling": "devdefault",
                },
                description="Temperature Zone 1",
                state=0,
                output="Temperature: 42.0°C\nTemperature: 42.0°C\nConfiguration: prefer device levels over user levels (used device levels)",
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[sample_host_name],
            ),
            CheckPreviewEntry(
                check_source="active",
                check_plugin_name="cmk_inv",
                ruleset_name=None,
                discovery_ruleset_name=None,
                item="Check_MK HW/SW Inventory",
                old_discovered_parameters={},
                new_discovered_parameters={},
                effective_parameters={"status_data_inventory": True},
                description="Check_MK HW/SW Inventory",
                state=None,
                output="WAITING - Active check, cannot be done offline",
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[sample_host_name],
            ),
        ],
        nodes_check_table={},
        host_labels={
            "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
            "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
        },
        new_labels={
            "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
            "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
        },
        vanished_labels={},
        changed_labels={},
        sources={"agent": (0, "Success")},
        labels_by_host={
            sample_host_name: [
                HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
                HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
            ],
        },
    )

    discovery_result = perform_fix_all(
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.FIX_ALL,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            raise_errors=True,
        ),
        host=sample_host,
        raise_errors=True,
    )
    sample_autochecks: Mapping[ServiceName, AutocheckEntry] = {
        "Temperature Zone 1": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 1", {}, {}),
    }
    mock_set_autochecks.assert_called_with(
        "NO_SITE",
        SetAutochecksInput(
            sample_host_name,
            sample_autochecks,
            {},
        ),
    )
    mock_discovery_preview.assert_called_once()
    assert [entry.check_source for entry in discovery_result.check_table] == [
        "unchanged",
        "active",
    ]
    assert discovery_result.new_labels == {}

    store = AuditLogStore()
    assert [
        log_entry.text for log_entry in store.read() if log_entry.action == "update-host-labels"
    ] == [f"Updated discovered host labels of '{sample_host_name}' with 2 labels"]


@pytest.mark.usefixtures("inline_background_jobs")
def test_perform_discovery_single_update(
    mocker: MockerFixture,
    sample_host_name: HostName,
    sample_host: Host,
    mock_set_autochecks: MagicMock,
) -> None:
    mock_discovery_preview = mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview",
        return_value=ServiceDiscoveryPreviewResult(
            output="",
            check_table=[
                CheckPreviewEntry(
                    check_source="unchanged",
                    check_plugin_name="checkmk_agent",
                    ruleset_name="agent_update",
                    discovery_ruleset_name=None,
                    item=None,
                    old_discovered_parameters={},
                    new_discovered_parameters={},
                    effective_parameters={
                        "agent_version": ("ignore", {}),
                        "agent_version_missmatch": 1,
                        "restricted_address_mismatch": 1,
                        "legacy_pull_mode": 1,
                    },
                    description="Check_MK Agent",
                    state=1,
                    output=(
                        "Version: 2022.05.23, OS: linux, TLS is not activated on monitored host"
                        " (see details)(!), Agent plug-ins: 0, Local checks: 0\nVersion:"
                        " 2022.05.23\nOS: linux\nThe hosts agent supports TLS, but it is not"
                        " being used.\nWe strongly recommend to enable TLS by registering the host"
                        " to the site (using the `cmk-agent-ctl register` command on the monitored"
                        " host).\nNOTE: A registered host will refuse all unencrypted connections."
                        " If the host is monitored by multiple sites, you must register to all of"
                        " them. This can be problematic if you are monitoring the same host from a"
                        " site running Checkmk version 2.0 or earlier.\nIf you can not register"
                        ' the host, you can configure missing TLS to be OK in the setting "State'
                        ' in case of available but not enabled TLS" of the ruleset "Checkmk Agent'
                        ' installation auditing".(!)\nAgent plug-ins: 0\nLocal checks: 0'
                    ),
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[HostName("TODAY")],
                ),
                CheckPreviewEntry(
                    check_source="unchanged",
                    check_plugin_name="mem_linux",
                    ruleset_name="memory_linux",
                    discovery_ruleset_name=None,
                    item=None,
                    old_discovered_parameters={},
                    new_discovered_parameters={},
                    effective_parameters={
                        "levels_virtual": ("perc_used", (80.0, 90.0)),
                        "levels_total": ("perc_used", (120.0, 150.0)),
                        "levels_shm": ("perc_used", (20.0, 30.0)),
                        "levels_pagetables": ("perc_used", (8.0, 16.0)),
                        "levels_committed": ("perc_used", (100.0, 150.0)),
                        "levels_commitlimit": ("perc_free", (20.0, 10.0)),
                        "levels_vmalloc": ("abs_free", (52428800, 31457280)),
                        "levels_hardwarecorrupted": ("abs_used", (1, 1)),
                    },
                    description="Memory",
                    state=0,
                    output=(
                        "Total virtual memory: 23.14% - 7.41 GB of 32.04 GB\n"
                        "Total virtual memory: 23.14% - 7.41 GB of 32.04 GB\n"
                        "RAM: 23.72% - 7.37 GB of 31.08 GB\n"
                        "Swap: 4.07% - 39.75 MB of 976.00 MB\n"
                        "Committed: 65.38% - 20.95 GB of 32.04 GB virtual memory\n"
                        "Commit Limit: 48.51% - 15.54 GB of 32.04 GB virtual memory\n"
                        "Shared memory: 6.66% - 2.07 GB of 31.08 GB RAM\n"
                        "Page tables: 0.22% - 71.04 MB of 31.08 GB RAM\n"
                        "Disk Writeback: 0.008% - 2.50 MB of 31.08 GB RAM\n"
                        "RAM available: 67.55% free - 21.00 GB of 31.08 GB\n"
                        "Hardware Corrupted: 0% - 0.00 B of 31.08 GB RAM"
                    ),
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[HostName("TODAY")],
                ),
            ],
            nodes_check_table={},
            host_labels={
                "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
                "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
            },
            new_labels={},
            vanished_labels={},
            changed_labels={},
            source_results={"agent": (0, "Success")},
            labels_by_host={
                HostName("TODAY"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
                    HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
                ],
            },
        ),
    )
    previous_discovery_result = DiscoveryResult(
        job_status={
            "duration": 2.351154088973999,
            "estimated_duration": 2.37550950050354,
            "host_name": HostName("TODAY"),
            "logfile_path": "~/var/log/web.log",
            "pid": 1363226,
            "ppid": 1363225,
            "started": 1654173769.3507118,
            "state": "finished",
            "stoppable": True,
            "title": "Refresh",
            "user": "cmkadmin",
            "loginfo": {
                "JobProgressUpdate": ["Starting job...", "Completed."],
                "JobResult": [],
                "JobException": [],
            },
            "is_active": False,
        },
        check_table_created=1654237821,
        check_table=[
            CheckPreviewEntry(
                check_source="unchanged",
                check_plugin_name="checkmk_agent",
                ruleset_name="agent_update",
                discovery_ruleset_name=None,
                item=None,
                old_discovered_parameters={},
                new_discovered_parameters={},
                effective_parameters={
                    "agent_version": ("ignore", {}),
                    "agent_version_missmatch": 1,
                    "restricted_address_mismatch": 1,
                    "legacy_pull_mode": 1,
                },
                description="Check_MK Agent",
                state=1,
                output=(
                    "Version: 2022.05.23, OS: linux, TLS is not activated on monitored host"
                    " (see details)(!), Agent plug-ins: 0, Local checks: 0\nVersion: 2022.05.23\n"
                    "OS: linux\nThe hosts agent supports TLS, but it is not being used.\n"
                    "We strongly recommend to enable TLS by registering the host to the site"
                    " (using the `cmk-agent-ctl register` command on the monitored host).\n"
                    "NOTE: A registered host will refuse all unencrypted connections. If the"
                    " host is monitored by multiple sites, you must register to all of them."
                    " This can be problematic if you are monitoring the same host from a site"
                    " running Checkmk version 2.0 or earlier.\nIf you can not register the host,"
                    ' you can configure missing TLS to be OK in the setting "State in case of'
                    ' available but not enabled TLS" of the ruleset "Checkmk Agent installation'
                    ' auditing".(!)\nAgent plug-ins: 0\nLocal checks: 0'
                ),
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[HostName("TODAY")],
            ),
            CheckPreviewEntry(
                check_source="new",
                check_plugin_name="mem_linux",
                ruleset_name="memory_linux",
                discovery_ruleset_name=None,
                item=None,
                old_discovered_parameters={},
                new_discovered_parameters={},
                effective_parameters={
                    "levels_virtual": ("perc_used", (80.0, 90.0)),
                    "levels_total": ("perc_used", (120.0, 150.0)),
                    "levels_shm": ("perc_used", (20.0, 30.0)),
                    "levels_pagetables": ("perc_used", (8.0, 16.0)),
                    "levels_committed": ("perc_used", (100.0, 150.0)),
                    "levels_commitlimit": ("perc_free", (20.0, 10.0)),
                    "levels_vmalloc": ("abs_free", (52428800, 31457280)),
                    "levels_hardwarecorrupted": ("abs_used", (1, 1)),
                },
                description="Memory",
                state=0,
                output=(
                    "Total virtual memory: 23.14% - 7.41 GB of 32.04 GB\n"
                    "Total virtual memory: 23.14% - 7.41 GB of 32.04 GB\n"
                    "RAM: 23.72% - 7.37 GB of 31.08 GB\n"
                    "Swap: 4.07% - 39.75 MB of 976.00 MB\n"
                    "Committed: 65.38% - 20.95 GB of 32.04 GB virtual memory\n"
                    "Commit Limit: 48.51% - 15.54 GB of 32.04 GB virtual memory\n"
                    "Shared memory: 6.66% - 2.07 GB of 31.08 GB RAM\n"
                    "Page tables: 0.22% - 71.04 MB of 31.08 GB RAM\n"
                    "Disk Writeback: 0.008% - 2.50 MB of 31.08 GB RAM\n"
                    "RAM available: 67.55% free - 21.00 GB of 31.08 GB\n"
                    "Hardware Corrupted: 0% - 0.00 B of 31.08 GB RAM"
                ),
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[HostName("TODAY")],
            ),
        ],
        nodes_check_table={},
        host_labels={
            "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
            "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
        },
        new_labels={},
        vanished_labels={},
        changed_labels={},
        sources={"agent": (0, "Success")},
        labels_by_host={
            HostName("TODAY"): [
                HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
                HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
            ],
        },
    )

    discovery_result = perform_service_discovery(
        action=DiscoveryAction.SINGLE_UPDATE,
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.SINGLE_UPDATE,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            raise_errors=True,
        ),
        selected_services=(("mem_linux", None),),
        update_source="new",
        update_target="unchanged",
        host=sample_host,
        raise_errors=True,
    )
    sample_autochecks: Mapping[ServiceName, AutocheckEntry] = {
        "Check_MK Agent": AutocheckEntry(CheckPluginName("checkmk_agent"), None, {}, {}),
        "Memory": AutocheckEntry(CheckPluginName("mem_linux"), None, {}, {}),
    }
    mock_set_autochecks.assert_called_with(
        "NO_SITE",
        SetAutochecksInput(
            sample_host_name,
            sample_autochecks,
            {},
        ),
    )
    mock_discovery_preview.assert_called_with(
        sample_host_name, prevent_fetching=False, raise_errors=False
    )
    assert [
        entry.check_source
        for entry in discovery_result.check_table
        if entry.check_plugin_name == "mem_linux"
    ] == ["unchanged"]

    store = AuditLogStore()
    assert [
        log_entry.text for log_entry in store.read() if log_entry.action == "set-autochecks"
    ] == [f"Saved check configuration of host '{sample_host_name}' with 2 services"]


def test_perform_discovery_action_update_services(
    mocker: MockerFixture,
    sample_host_name: HostName,
    sample_host: Host,
    mock_set_autochecks: MagicMock,
) -> None:
    mock_discovery_preview = mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview",
        return_value=ServiceDiscoveryPreviewResult(
            output="",
            check_table=[
                CheckPreviewEntry(
                    check_source="unchanged",
                    check_plugin_name="df",
                    ruleset_name="filesystem",
                    discovery_ruleset_name=None,
                    item="/opt/omd/sites/heute/tmp",
                    old_discovered_parameters={
                        "mountpoint_for_block_devices": "volume_name",
                        "item_appearance": "mountpoint",
                    },
                    new_discovered_parameters={
                        "mountpoint_for_block_devices": "volume_name",
                        "item_appearance": "mountpoint",
                    },
                    effective_parameters={
                        "levels": (80.0, 90.0),
                        "magic_normsize": 20,
                        "levels_low": (50.0, 60.0),
                        "trend_range": 24,
                        "trend_perfdata": True,
                        "show_levels": "onmagic",
                        "inodes_levels": (10.0, 5.0),
                        "show_inodes": "onlow",
                        "show_reserved": False,
                        "mountpoint_for_block_devices": "volume_name",
                        "item_appearance": "mountpoint",
                    },
                    description="Filesystem /opt/omd/sites/heute/tmp",
                    state=0,
                    output="0.04% used (5.59 MB of 15.54 GB), trend: -89.23 kB / 24 hours\n0.04% used (5.59 MB of 15.54 GB)\ntrend: -89.23 kB / 24 hours",
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[HostName("TODAY")],
                ),
            ],
            nodes_check_table={},
            host_labels={
                "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
                "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
            },
            new_labels={},
            vanished_labels={},
            changed_labels={},
            source_results={"agent": (0, "Success")},
            labels_by_host={
                HostName("TODAY"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
                    HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
                ],
            },
        ),
    )
    previous_discovery_result = DiscoveryResult(
        job_status={
            "duration": 2.351154088973999,
            "estimated_duration": 2.37550950050354,
            "host_name": "TODAY",
            "logfile_path": "~/var/log/web.log",
            "pid": 1363226,
            "ppid": 1363225,
            "started": 1654173769.3507118,
            "state": "finished",
            "stoppable": True,
            "title": "Refresh",
            "user": "cmkadmin",
            "loginfo": {
                "JobProgressUpdate": ["Starting job...", "Completed."],
                "JobResult": [],
                "JobException": [],
            },
            "is_active": False,
        },
        check_table_created=1654237821,
        check_table=[
            CheckPreviewEntry(
                check_source="new",
                check_plugin_name="df",
                ruleset_name="filesystem",
                discovery_ruleset_name=None,
                item="/opt/omd/sites/heute/tmp",
                old_discovered_parameters={
                    "mountpoint_for_block_devices": "volume_name",
                    "item_appearance": "mountpoint",
                },
                new_discovered_parameters={
                    "mountpoint_for_block_devices": "volume_name",
                    "item_appearance": "mountpoint",
                },
                effective_parameters={
                    "levels": (80.0, 90.0),
                    "magic_normsize": 20,
                    "levels_low": (50.0, 60.0),
                    "trend_range": 24,
                    "trend_perfdata": True,
                    "show_levels": "onmagic",
                    "inodes_levels": (10.0, 5.0),
                    "show_inodes": "onlow",
                    "show_reserved": False,
                    "mountpoint_for_block_devices": "volume_name",
                    "item_appearance": "mountpoint",
                },
                description="Filesystem /opt/omd/sites/heute/tmp",
                state=0,
                output="0.04% used (5.78 MB of 15.54 GB), trend: +10.38 kB / 24 hours\n0.04% used (5.78 MB of 15.54 GB)\ntrend: +10.38 kB / 24 hours",
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[HostName("TODAY")],
            ),
            CheckPreviewEntry(
                check_source="vanished",
                check_plugin_name="lnx_if",
                ruleset_name="dummy_name",
                discovery_ruleset_name=None,
                item="2",
                old_discovered_parameters={
                    "discovered_oper_status": ["1"],
                    "discovered_speed": 10000000,
                },
                new_discovered_parameters={
                    "discovered_oper_status": ["1"],
                    "discovered_speed": 10000000,
                },
                effective_parameters={
                    "errors": {"both": ("perc", (0.01, 0.1))},
                    "discovered_oper_status": ["1"],
                    "discovered_speed": 10000000,
                },
                description="Interface 2",
                state=2,
                output="[docker0], (down)(!!), MAC: 02:42:E3:80:F5:EE, Speed: 10 MBit/s (assumed)\n[docker0]\nOperational state: down(!!)\nMAC: 02:42:E3:80:F5:EE\nSpeed: 10 MBit/s (assumed)",
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[HostName("TODAY")],
            ),
        ],
        nodes_check_table={},
        host_labels={
            "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
            "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
        },
        new_labels={},
        vanished_labels={},
        changed_labels={},
        sources={"agent": (0, "Success")},
        labels_by_host={
            HostName("TODAY"): [
                HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
                HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
            ],
        },
    )

    discovery_result = perform_service_discovery(
        action=DiscoveryAction.UPDATE_SERVICES,
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.UPDATE_SERVICES,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            raise_errors=True,
        ),
        selected_services=EVERYTHING,
        update_source=None,
        update_target=None,
        host=sample_host,
        raise_errors=True,
    )
    sample_autochecks: Mapping[ServiceName, AutocheckEntry] = {
        "Filesystem /opt/omd/sites/heute/tmp": AutocheckEntry(
            CheckPluginName("df"),
            "/opt/omd/sites/heute/tmp",
            {
                "item_appearance": "mountpoint",
                "mountpoint_for_block_devices": "volume_name",
            },
            {},
        )
    }
    mock_set_autochecks.assert_called_with(
        "NO_SITE",
        SetAutochecksInput(
            sample_host_name,
            sample_autochecks,
            {},
        ),
    )
    mock_discovery_preview.assert_called_with(
        sample_host_name, prevent_fetching=False, raise_errors=False
    )
    assert [entry.check_source for entry in discovery_result.check_table] == ["unchanged"]

    store = AuditLogStore()
    assert [
        log_entry.text for log_entry in store.read() if log_entry.action == "set-autochecks"
    ] == [f"Saved check configuration of host '{sample_host_name}' with 1 services"]


def test_perform_discovery_action_update_host_labels(
    mocker: MockerFixture,
    sample_host_name: HostName,
    sample_host: Host,
    mock_set_autochecks: MagicMock,
) -> None:
    mock_update_host_labels = mocker.patch(
        "cmk.gui.watolib.services.update_host_labels", return_value=None
    )
    mock_discovery_preview = mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview",
        return_value=ServiceDiscoveryPreviewResult(
            output="",
            check_table=[],
            nodes_check_table={},
            host_labels={
                "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
            },
            new_labels={},
            vanished_labels={},
            changed_labels={},
            source_results={"agent": (0, "Success")},
            labels_by_host={
                HostName(sample_host_name): [
                    HostLabel("cmk/os_family", "linux", SectionName("check_mk"))
                ],
            },
        ),
    )
    previous_discovery_result = DiscoveryResult(
        job_status={
            "duration": 2.351154088973999,
            "estimated_duration": 2.37550950050354,
            "host_name": "heute",
            "logfile_path": "~/var/log/web.log",
            "pid": 1363226,
            "ppid": 1363225,
            "started": 1654173769.3507118,
            "state": "finished",
            "stoppable": True,
            "title": "Refresh",
            "user": "cmkadmin",
            "loginfo": {
                "JobProgressUpdate": ["Starting job...", "Completed."],
                "JobResult": [],
                "JobException": [],
            },
            "is_active": False,
        },
        check_table_created=1654248127,
        check_table=[],
        nodes_check_table={},
        host_labels={
            # "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
            "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
        },
        new_labels={},
        vanished_labels={"cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"}},
        changed_labels={},
        sources={"agent": (0, "Success")},
        labels_by_host={
            HostName(sample_host_name): [
                HostLabel("cmk/os_family", "linux", SectionName("check_mk"))
            ],
        },
    )

    discovery_result = perform_host_label_discovery(
        action=DiscoveryAction.UPDATE_HOST_LABELS,
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.UPDATE_HOST_LABELS,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            raise_errors=True,
        ),
        host=sample_host,
        raise_errors=True,
    )

    mock_update_host_labels.assert_called_once_with(
        "NO_SITE",
        sample_host_name,
        [
            # HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
            HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
        ],
    )
    mock_set_autochecks.assert_not_called()
    mock_discovery_preview.assert_called_with(
        sample_host_name, prevent_fetching=False, raise_errors=False
    )
    assert "cmk/check_mk_server" not in discovery_result.host_labels

    store = AuditLogStore()
    assert [
        log_entry.text for log_entry in store.read() if log_entry.action == "update-host-labels"
    ] == [f"Updated discovered host labels of '{sample_host_name}' with 1 labels"]
