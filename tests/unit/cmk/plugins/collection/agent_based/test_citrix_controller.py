#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.citrix_controller import (
    check_citrix_controller,
    check_citrix_controller_licensing,
    check_citrix_controller_registered,
    check_citrix_controller_services,
    check_citrix_controller_sessions,
    DesktopParams,
    discovery_citrix_controller,
    discovery_citrix_controller_licensing,
    discovery_citrix_controller_registered,
    discovery_citrix_controller_services,
    discovery_citrix_controller_sessions,
    SessionParams,
)
from cmk.plugins.lib.citrix_controller import parse_citrix_controller, Section

STRING_TABLE = [
    ["ControllerState", "Active"],
    ["ControllerVersion", "7.6.0.5024"],
    ["DesktopsRegistered", "29"],
    ["LicensingServerState", "OK"],
    ["LicensingGraceState", "NotActive"],
    ["ActiveSiteServices", "XenPool01", "-", "Cisco", "UCS", "VMware"],
    ["TotalFarmActiveSessions", "262"],
    ["TotalFarmInactiveSessions", "14"],
]

STRING_TABLE_2 = [
    ["ControllerState"],
    ["ControllerVersion"],
    ["DesktopsRegistered"],
    ["LicensingServerState"],
    ["LicensingGraceState"],
    ["ActiveSiteServices"],
    ["TotalFarmActiveSessions", "0"],
    ["TotalFarmInactiveSessions", "0"],
]


STRING_TABLE_3 = [
    ["ControllerState", "Active"],
    ["ControllerVersion", "7.18.0.21"],
    ["DesktopsRegistered", "13"],
    ["LicensingServerState", "OK"],
    ["LicensingGraceState", "Expired"],
    [
        "ActiveSiteServices",
        "ControllerReaper",
        "ControllerNameCacheRefresh",
        "Licensing",
        "BrokerReaper",
        "RegistrationHardening",
        "WorkerNameCacheRefresh",
        "AccountNameCacheRefresh",
        "PowerPolicy",
        "GroupUsage",
        "AddressNameResolver",
        "RebootScheduleManager",
        "RebootCycleManager",
        "ScopeNamesRefresh",
        "FeatureChecks",
        "RemotePC",
        "IdleSessionManager",
        "OperationalEventsService",
        "ConfigurationExport",
        "LicenseTypeChanged",
    ],
    ["TotalFarmActiveSessions", "128"],
    ["TotalFarmInactiveSessions", "13"],
    ["ControllerState", "Active"],
    ["ControllerVersion", "7.18.0.21"],
    ["DesktopsRegistered", "13"],
    ["LicensingServerState", "OK"],
    ["LicensingGraceState", "Expired"],
    [
        "ActiveSiteServices",
        "ControllerReaper",
        "ControllerNameCacheRefresh",
        "Licensing",
        "BrokerReaper",
        "RegistrationHardening",
        "WorkerNameCacheRefresh",
        "AccountNameCacheRefresh",
        "PowerPolicy",
        "GroupUsage",
        "AddressNameResolver",
        "RebootScheduleManager",
        "RebootCycleManager",
        "ScopeNamesRefresh",
        "FeatureChecks",
        "RemotePC",
        "IdleSessionManager",
        "OperationalEventsService",
        "ConfigurationExport",
        "LicenseTypeChanged",
    ],
    ["TotalFarmActiveSessions", "128"],
    ["TotalFarmInactiveSessions", "13"],
]


@pytest.fixture(name="section", params=[STRING_TABLE, STRING_TABLE_2, STRING_TABLE_3])
def fixture_section(request: pytest.FixtureRequest) -> Section:
    section = parse_citrix_controller(request.param)
    assert section is not None
    return section


def test_discovery_controller(section: Section) -> None:
    assert list(discovery_citrix_controller(section))


def test_discovery_controller_licensing(section: Section) -> None:
    assert list(discovery_citrix_controller_licensing(section))


def test_discovery_controller_registered(section: Section) -> None:
    assert list(discovery_citrix_controller_registered(section))


def test_discovery_controller_services(section: Section) -> None:
    assert list(discovery_citrix_controller_services(section))


def test_discovery_controller_sessions(section: Section) -> None:
    assert list(discovery_citrix_controller_sessions(section))


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (STRING_TABLE, [Result(state=State.OK, summary="Active")]),
        (STRING_TABLE_2, [Result(state=State.UNKNOWN, summary="unknown")]),
    ],
)
def test_check_controller(string_table: StringTable, expected: CheckResult) -> None:
    section = parse_citrix_controller(string_table)
    assert section is not None
    assert list(check_citrix_controller(section)) == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            STRING_TABLE,
            [
                Result(state=State.OK, summary="Licensing Server State: OK"),
                Result(state=State.OK, summary="Licensing Grace State: not active"),
            ],
        ),
        (
            STRING_TABLE_2,
            [],
        ),
        (
            STRING_TABLE_3,
            [
                Result(state=State.OK, summary="Licensing Server State: OK"),
                Result(state=State.CRIT, summary="Licensing Grace State: expired"),
            ],
        ),
    ],
)
def test_check_controller_licensing(string_table: StringTable, expected: CheckResult) -> None:
    section = parse_citrix_controller(string_table)
    assert section is not None
    assert list(check_citrix_controller_licensing(section)) == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            STRING_TABLE,
            [Result(state=State.OK, summary="29"), Metric("registered_desktops", 29.0)],
        ),
        (
            STRING_TABLE_2,
            [Result(state=State.UNKNOWN, summary="No desktops registered")],
        ),
    ],
)
def test_check_controller_registered(string_table: StringTable, expected: CheckResult) -> None:
    section = parse_citrix_controller(string_table)
    assert section is not None
    assert list(check_citrix_controller_registered(DesktopParams(), section)) == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (STRING_TABLE, [Result(state=State.OK, summary="XenPool01 - Cisco UCS VMware")]),
        (STRING_TABLE_2, [Result(state=State.OK, summary="No services")]),
        (
            STRING_TABLE_3,
            [
                Result(
                    state=State.OK,
                    summary="ControllerReaper ControllerNameCacheRefresh Licensing BrokerReaper RegistrationHardening WorkerNameCacheRefresh AccountNameCacheRefresh PowerPolicy GroupUsage AddressNameResolver RebootScheduleManager RebootCycleManager ScopeNamesRefresh FeatureChecks RemotePC IdleSessionManager OperationalEventsService ConfigurationExport LicenseTypeChanged",
                )
            ],
        ),
    ],
)
def test_check_controller_services(string_table: StringTable, expected: CheckResult) -> None:
    section = parse_citrix_controller(string_table)
    assert section is not None
    assert list(check_citrix_controller_services(section)) == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            STRING_TABLE,
            [
                Result(state=State.OK, summary="total: 276"),
                Metric("total_sessions", 276.0),
                Result(state=State.OK, summary="active: 262"),
                Metric("active_sessions", 262.0),
                Result(state=State.OK, summary="inactive: 14"),
                Metric("inactive_sessions", 14.0),
            ],
        ),
        (
            STRING_TABLE_2,
            [
                Result(state=State.OK, summary="total: 0"),
                Metric("total_sessions", 0.0),
                Result(state=State.OK, summary="active: 0"),
                Metric("active_sessions", 0.0),
                Result(state=State.OK, summary="inactive: 0"),
                Metric("inactive_sessions", 0.0),
            ],
        ),
    ],
)
def test_check_controller_sessions(string_table: StringTable, expected: CheckResult) -> None:
    section = parse_citrix_controller(string_table)
    assert section is not None
    assert list(check_citrix_controller_sessions(SessionParams(), section)) == expected
