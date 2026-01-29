#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"

import json
from collections.abc import Generator, Mapping, Sequence
from unittest.mock import call, MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from cmk.automations.results import (
    DeleteHostsResult,
    ServiceDiscoveryPreviewResult,
    SetAutochecksInput,
    SetAutochecksV2Result,
)
from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName, SectionName
from cmk.gui.utils import transaction_manager
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host
from cmk.gui.watolib.services import (
    Discovery,
    DiscoveryAction,
    DiscoveryResult,
    DiscoveryTransition,
    get_check_table,
    initial_discovery_result,
    perform_fix_all,
    perform_host_label_discovery,
    perform_service_discovery,
)
from cmk.utils.automation_config import LocalAutomationConfig
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.labels import HostLabel
from cmk.utils.servicename import ServiceName

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
    config_warnings=["Ihr Dualband ist gerissen. Bitte legen Sie ein neues ein."],
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
def fixture_check_transaction() -> object:
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
) -> Generator[Host]:
    hostname = sample_host_name
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts([(hostname, {}, None)], pprint_value=False, use_git=False)
    host = root_folder.host(hostname)
    assert host is not None
    yield host
    root_folder.delete_hosts(
        [hostname],
        automation=lambda *args, **kwargs: DeleteHostsResult(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )


def test_discovery_action_json_serializable() -> None:
    assert [json.dumps(a) for a in DiscoveryAction] == [
        '""',
        '"stop"',
        '"fix_all"',
        '"refresh"',
        '"tabula_rasa"',
        '"single_update"',
        '"bulk_update"',
        '"update_host_labels"',
        '"update_services"',
        '"update_service_labels"',
        '"update_discovery_parameters"',
        '"single_update_service_properties"',
    ]


@pytest.mark.usefixtures("inline_background_jobs")
def test_perform_discovery_none_action(
    sample_host: Host, mock_discovery_preview: MagicMock
) -> None:
    discovery_result = initial_discovery_result(
        action=DiscoveryAction.NONE,
        host=sample_host,
        previous_discovery_result=None,
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        raise_errors=True,
        debug=False,
        use_git=False,
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
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        raise_errors=True,
        debug=False,
        use_git=False,
    )

    mock_discovery.assert_called_once()
    mock_discovery_preview.assert_has_calls(
        [
            call(sample_host_name, prevent_fetching=False, raise_errors=False, debug=False),
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
            config_warnings=["We're all alone."],
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
        config_warnings=["Nothing lasts forever."],
    )

    discovery_result = perform_fix_all(
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.FIX_ALL,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            automation_config=LocalAutomationConfig(),
            user_permission_config=UserPermissionSerializableConfig({}, {}, []),
            raise_errors=True,
            debug=False,
            use_git=False,
        ),
        host=sample_host,
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        raise_errors=True,
        pprint_value=False,
        debug=False,
        use_git=False,
    )
    sample_autochecks: Mapping[ServiceName, AutocheckEntry] = {
        "Temperature Zone 1": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 1", {}, {}),
    }
    mock_set_autochecks.assert_called_with(
        LocalAutomationConfig(),
        SetAutochecksInput(
            sample_host_name,
            sample_autochecks,
            {},
        ),
        debug=False,
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
            config_warnings=["Your feet have expired."],
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
        config_warnings=(),
    )

    discovery_result = perform_service_discovery(
        action=DiscoveryAction.SINGLE_UPDATE,
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.SINGLE_UPDATE,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            automation_config=LocalAutomationConfig(),
            user_permission_config=UserPermissionSerializableConfig({}, {}, []),
            raise_errors=True,
            debug=False,
            use_git=False,
        ),
        selected_services=(("mem_linux", None),),
        update_source="new",
        update_target="unchanged",
        host=sample_host,
        raise_errors=True,
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        pprint_value=False,
        debug=False,
        use_git=False,
    )
    sample_autochecks: Mapping[ServiceName, AutocheckEntry] = {
        "Check_MK Agent": AutocheckEntry(CheckPluginName("checkmk_agent"), None, {}, {}),
        "Memory": AutocheckEntry(CheckPluginName("mem_linux"), None, {}, {}),
    }
    mock_set_autochecks.assert_called_with(
        LocalAutomationConfig(),
        SetAutochecksInput(
            sample_host_name,
            sample_autochecks,
            {},
        ),
        debug=False,
    )
    mock_discovery_preview.assert_called_with(
        sample_host_name,
        prevent_fetching=True,
        raise_errors=False,
        debug=False,
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


@pytest.mark.usefixtures("inline_background_jobs")
def test_perform_discovery_single_update__ignore(
    mocker: MockerFixture,
    sample_host_name: HostName,
    sample_host: Host,
    mock_set_autochecks: MagicMock,
) -> None:
    mock_save_function = mocker.patch(
        "cmk.gui.watolib.services.Discovery._save_host_service_enable_disable_rules",
        return_value=None,
    )
    mocker.patch(
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
                    check_plugin_name="mssql_instance",
                    ruleset_name="mssql_instance",
                    discovery_ruleset_name=None,
                    item="S2DT",
                    old_discovered_parameters={},
                    new_discovered_parameters={},
                    effective_parameters={},
                    description="MSSQL S2DT Instance",
                    state=0,
                    output="nobody cares",
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[HostName("host23")],
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
                HostName("host23"): [],
            },
            config_warnings=(),
        ),
    )

    previous_discovery_result = DiscoveryResult(
        job_status={
            "state": "finished",
            "started": 1764593093.764405,
            "pid": 604583,
            "loginfo": {"JobProgressUpdate": [], "JobResult": [], "JobException": []},
            "is_active": False,
            "duration": 0.36932802200317383,
            "title": "Refresh",
            "stoppable": True,
            "deletable": True,
            "user": "cmkadmin",
            "estimated_duration": 0.0,
            "ppid": 604485,
            "logfile_path": "~/var/log/web.log",
            "acknowledged_by": None,
            "lock_wato": False,
            "host_name": sample_host_name,
        },
        check_table_created=1764596025,
        check_table=[
            CheckPreviewEntry(
                check_source="unchanged",
                check_plugin_name="mssql_instance",
                ruleset_name="mssql_instance",
                discovery_ruleset_name=None,
                item="S2DT",
                old_discovered_parameters={},
                new_discovered_parameters={},
                effective_parameters={},
                description="MSSQL S2DT Instance",
                state=0,
                output="nobody cares",
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[HostName("host23")],
            ),
        ],
        nodes_check_table={
            HostName("host22"): [],
            HostName("host23"): [
                CheckPreviewEntry(
                    check_source="clustered_old",
                    check_plugin_name="mssql_instance",
                    ruleset_name="mssql_instance",
                    discovery_ruleset_name=None,
                    item="S2DT",
                    old_discovered_parameters={},
                    new_discovered_parameters={},
                    effective_parameters={},
                    description="MSSQL S2DT Instance",
                    state=0,
                    output="nobody cares",
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[HostName("host23")],
                )
            ],
        },
        host_labels={},
        new_labels={},
        vanished_labels={},
        changed_labels={},
        labels_by_host={HostName("host22"): [], HostName("host23"): [], sample_host_name: []},
        sources={
            "agent": (0, "[agent] Success"),
            "piggyback": (0, "[piggyback] Success (but no data found for this host)"),
        },
        config_warnings=(),
    )

    perform_service_discovery(
        action=DiscoveryAction.SINGLE_UPDATE,
        discovery_result=previous_discovery_result,
        selected_services=(("mssql_instance", "S2DT"),),
        update_source="unchanged",
        update_target="ignored",
        host=sample_host,
        raise_errors=True,
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        pprint_value=False,
        debug=False,
        use_git=False,
    )
    mock_save_function.assert_called_once()
    remove_disabled_rule, add_disabled_rule, *_ = mock_save_function.call_args_list[0][0]
    assert len(remove_disabled_rule) == 0
    assert add_disabled_rule == {"MSSQL S2DT Instance"}


@pytest.mark.usefixtures("inline_background_jobs")
class TestPerformDiscoverySingleUpdate:
    check_table = [
        CheckPreviewEntry(
            check_source="unchanged",
            check_plugin_name="some_plugin",
            ruleset_name="some_rule",
            discovery_ruleset_name=None,
            item="A",
            old_discovered_parameters={},
            new_discovered_parameters={},
            effective_parameters={},
            description="Description A",
            state=1,
            output="Lorem ipsum",
            metrics=[],
            old_labels={},
            new_labels={},
            found_on_nodes=[],
        ),
        CheckPreviewEntry(
            check_source="ignored",
            check_plugin_name="other_plugin",
            ruleset_name="some_rule",
            discovery_ruleset_name=None,
            item="B",
            old_discovered_parameters={},
            new_discovered_parameters={},
            effective_parameters={},
            description="Description B",
            state=1,
            output="Lorem ipsum",
            metrics=[],
            old_labels={},
            new_labels={},
            found_on_nodes=[],
        ),
        CheckPreviewEntry(
            check_source="unchanged",
            check_plugin_name="some_plugin",
            ruleset_name="some_rule",
            discovery_ruleset_name=None,
            item="B",
            old_discovered_parameters={},
            new_discovered_parameters={},
            effective_parameters={},
            description="Description B",
            state=1,
            output="Lorem ipsum",
            metrics=[],
            old_labels={},
            new_labels={},
            found_on_nodes=[],
        ),
    ]

    def _perform_discovery(
        self,
        mocker: MockerFixture,
        sample_host_name: HostName,
        sample_host: Host,
        selected_serives: tuple[tuple[str, str | None]],
        update_source: str,
        update_target: str,
    ) -> tuple[DiscoveryResult, set[str], set[str]]:
        mock_save_function = mocker.patch(
            "cmk.gui.watolib.services.Discovery._save_host_service_enable_disable_rules",
            return_value=None,
        )
        mocker.patch(
            "cmk.gui.watolib.services.local_discovery_preview",
            return_value=ServiceDiscoveryPreviewResult(
                output="",
                check_table=self.check_table,
                nodes_check_table={},
                host_labels={
                    "cmk/check_mk_server": {"value": "yes", "plugin_name": "omd_info"},
                    "cmk/os_family": {"value": "linux", "plugin_name": "check_mk"},
                },
                new_labels={},
                vanished_labels={},
                changed_labels={},
                source_results={"agent": (0, "Success")},
                labels_by_host={},
                config_warnings=[],
            ),
        )
        result = perform_service_discovery(
            action=DiscoveryAction.SINGLE_UPDATE,
            discovery_result=DiscoveryResult(
                job_status={
                    "state": "finished",
                    "started": 1764593093.764405,
                    "pid": 604583,
                    "loginfo": {"JobProgressUpdate": [], "JobResult": [], "JobException": []},
                    "is_active": False,
                    "duration": 0.36932802200317383,
                    "title": "Refresh",
                    "stoppable": True,
                    "deletable": True,
                    "user": "cmkadmin",
                    "estimated_duration": 0.0,
                    "ppid": 604485,
                    "logfile_path": "~/var/log/web.log",
                    "acknowledged_by": None,
                    "lock_wato": False,
                    "host_name": sample_host_name,
                },
                check_table_created=1764596025,
                check_table=self.check_table,
                nodes_check_table={},
                host_labels={},
                new_labels={},
                vanished_labels={},
                changed_labels={},
                labels_by_host={sample_host_name: []},
                sources={
                    "agent": (0, "[agent] Success"),
                    "piggyback": (0, "[piggyback] Success (but no data found for this host)"),
                },
                config_warnings=[],
            ),
            selected_services=selected_serives,
            update_source=update_source,
            update_target=update_target,
            host=sample_host,
            raise_errors=True,
            automation_config=LocalAutomationConfig(),
            user_permission_config=UserPermissionSerializableConfig({}, {}, []),
            pprint_value=False,
            debug=False,
            use_git=False,
        )

        mock_save_function.assert_called_once()
        remove_disabled_rule, add_disabled_rule, *_ = mock_save_function.call_args_list[0][0]
        return result, remove_disabled_rule, add_disabled_rule

    def test_dupes_are_not_disabled_automatically(
        self,
        mocker: MockerFixture,
        sample_host_name: HostName,
        sample_host: Host,
        mock_set_autochecks: MagicMock,
    ) -> None:
        """
        Ensure that no disabled rule gets created when there are duplicate services and one is
        discovery as disabled, e.g. because the check is disabled.
        """
        _, remove_disabled_rule, add_disabled_rule = self._perform_discovery(
            mocker=mocker,
            sample_host_name=sample_host_name,
            sample_host=sample_host,
            selected_serives=(("some_plugin", "A"),),
            update_source="unchanged",
            update_target="ignored",
        )

        assert len(remove_disabled_rule) == 0
        assert add_disabled_rule == {"Description A"}

    def test_dupes_are_disabled_manually(
        self,
        mocker: MockerFixture,
        sample_host_name: HostName,
        sample_host: Host,
        mock_set_autochecks: MagicMock,
    ) -> None:
        """
        Ensure that the disabled rule gets created, when a user explicitly wants to disable the
        service.
        """
        _, remove_disabled_rule, add_disabled_rule = self._perform_discovery(
            mocker=mocker,
            sample_host_name=sample_host_name,
            sample_host=sample_host,
            selected_serives=(("some_plugin", "B"),),
            update_source="unchanged",
            update_target="ignored",
        )

        assert len(remove_disabled_rule) == 0
        assert add_disabled_rule == {"Description B"}


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
            config_warnings=["The end is near."],
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
        config_warnings=(),
    )

    discovery_result = perform_service_discovery(
        action=DiscoveryAction.UPDATE_SERVICES,
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.UPDATE_SERVICES,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            automation_config=LocalAutomationConfig(),
            user_permission_config=UserPermissionSerializableConfig({}, {}, []),
            raise_errors=True,
            debug=False,
            use_git=False,
        ),
        selected_services=EVERYTHING,
        update_source=None,
        update_target=None,
        host=sample_host,
        raise_errors=True,
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        pprint_value=False,
        debug=False,
        use_git=False,
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
        LocalAutomationConfig(),
        SetAutochecksInput(
            sample_host_name,
            sample_autochecks,
            {},
        ),
        debug=False,
    )
    mock_discovery_preview.assert_called_with(
        sample_host_name,
        prevent_fetching=True,
        raise_errors=False,
        debug=False,
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
            config_warnings=(),
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
        config_warnings=(),
    )

    discovery_result = perform_host_label_discovery(
        action=DiscoveryAction.UPDATE_HOST_LABELS,
        discovery_result=initial_discovery_result(
            action=DiscoveryAction.UPDATE_HOST_LABELS,
            host=sample_host,
            previous_discovery_result=previous_discovery_result,
            automation_config=LocalAutomationConfig(),
            user_permission_config=UserPermissionSerializableConfig({}, {}, []),
            raise_errors=True,
            debug=False,
            use_git=False,
        ),
        host=sample_host,
        raise_errors=True,
        automation_config=LocalAutomationConfig(),
        user_permission_config=UserPermissionSerializableConfig({}, {}, []),
        pprint_value=False,
        debug=False,
        use_git=False,
    )

    mock_update_host_labels.assert_called_once_with(
        LocalAutomationConfig(),
        sample_host_name,
        [
            # HostLabel("cmk/check_mk_server", "yes", SectionName("omd_info")),
            HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
        ],
        debug=False,
    )
    mock_set_autochecks.assert_not_called()
    mock_discovery_preview.assert_called_with(
        sample_host_name,
        prevent_fetching=True,
        raise_errors=False,
        debug=False,
    )
    assert "cmk/check_mk_server" not in discovery_result.host_labels

    store = AuditLogStore()
    assert [
        log_entry.text for log_entry in store.read() if log_entry.action == "update-host-labels"
    ] == [f"Updated discovered host labels of '{sample_host_name}' with 1 labels"]


def _make_discovery_result(
    check_table: Sequence[CheckPreviewEntry],
    nodes_check_table: Mapping[HostName, Sequence[CheckPreviewEntry]],
) -> DiscoveryResult:
    """make a dummy discovery result from the values relevant for the test"""
    return DiscoveryResult(
        job_status={},
        check_table_created=0,
        check_table=check_table,
        nodes_check_table=nodes_check_table,
        host_labels={},
        new_labels={},
        vanished_labels={},
        changed_labels={},
        labels_by_host={},
        sources={},
        config_warnings=(),
    )


def _make_preview_entry(
    check_source: str,
    old_params: Mapping[str, object],
    new_params: Mapping[str, object],
    found_on_nodes: list[HostName],
) -> CheckPreviewEntry:
    """make a dummy preview entry from the values relevant for the test"""
    return CheckPreviewEntry(
        check_source=check_source,
        check_plugin_name="dummy_plugin",
        ruleset_name=None,
        discovery_ruleset_name=None,
        item=None,
        old_discovered_parameters=old_params,
        new_discovered_parameters=new_params,
        effective_parameters={},
        description="my-description",
        state=0,
        output="",
        metrics=[],
        old_labels={},
        new_labels={},
        found_on_nodes=found_on_nodes,
    )


def _make_autocheck_entry(parameter_value: str) -> AutocheckEntry:
    """make a dummy autocheck entry from the values relevant for the test"""
    return AutocheckEntry(
        check_plugin_name=CheckPluginName("dummy_plugin"),
        item=None,
        parameters={"p": parameter_value},
        service_labels={},
    )


def _grant_all_permissions(_p: object) -> None:
    pass


class TestDiscovery:
    @staticmethod
    def _make_clustered_service_vanished_result() -> DiscoveryResult:
        """Test scenario where a clustered service vanished from the primary node"""
        return _make_discovery_result(
            check_table=[
                _make_preview_entry(
                    check_source="changed",
                    old_params={"p": "old"},
                    new_params={"p": "new"},
                    found_on_nodes=[HostName("node2")],
                ),
            ],
            nodes_check_table={
                HostName("node1"): [
                    _make_preview_entry("clustered_vanished", {"p": "old"}, {"p": "old"}, []),
                ],
                HostName("node2"): [
                    _make_preview_entry(
                        "clustered_old", {"p": "new"}, {"p": "new"}, [HostName("node2")]
                    ),
                ],
            },
        )

    def test_cluster_discovery_removes_outdated_node_services_fix_all(self) -> None:
        """Tests that the discovery transition removes outdated node services
        if other nodes discover newer services.

        Failing to do this leads to wrong discovered parameters.
        """
        target_host = HostName("mycluster")
        discovery_result = self._make_clustered_service_vanished_result()
        assert Discovery(
            host=object(),  # type: ignore[arg-type] # not accessed in this test
            action=DiscoveryAction.FIX_ALL,
            update_target=None,
            selected_services=(),
            user_need_permission=_grant_all_permissions,
        ).compute_discovery_transition(discovery_result, target_host) == DiscoveryTransition(
            need_sync=False,
            add_disabled_rule=set(),
            remove_disabled_rule=set(),
            old_autochecks=SetAutochecksInput(
                discovered_host=target_host,
                target_services={"my-description": _make_autocheck_entry("old")},
                nodes_services={  # why is this empty?
                    HostName("node1"): {},
                    HostName("node2"): {},
                },
            ),
            new_autochecks=SetAutochecksInput(
                discovered_host=target_host,
                target_services={
                    "my-description": _make_autocheck_entry("new"),
                },
                nodes_services={
                    HostName("node1"): {},
                    HostName("node2"): {
                        "my-description": _make_autocheck_entry("new"),
                    },
                },
            ),
        )

    def test_cluster_discovery_removes_outdated_node_services_update_params(self) -> None:
        """Tests that the discovery transition removes outdated node services
        if other nodes discover newer services.

        Failing to do this leads to wrong discovered parameters.
        """
        target_host = HostName("mycluster")
        discovery_result = self._make_clustered_service_vanished_result()
        assert Discovery(
            host=object(),  # type: ignore[arg-type] # not accessed in this test
            action=DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS,
            update_target="unchanged",
            selected_services=(),
            user_need_permission=_grant_all_permissions,
        ).compute_discovery_transition(discovery_result, target_host) == DiscoveryTransition(
            need_sync=False,
            remove_disabled_rule=set(),
            add_disabled_rule=set(),
            old_autochecks=SetAutochecksInput(
                discovered_host=target_host,
                target_services={"my-description": _make_autocheck_entry("old")},
                nodes_services={  # why is this empty?
                    HostName("node1"): {},
                    HostName("node2"): {},
                },
            ),
            new_autochecks=SetAutochecksInput(
                discovered_host=target_host,
                target_services={"my-description": _make_autocheck_entry("new")},
                nodes_services={
                    HostName("node1"): {},
                    HostName("node2"): {"my-description": _make_autocheck_entry("new")},
                },
            ),
        )
