#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from datetime import datetime, UTC
from typing import Any, Literal

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.cisco.agent_based.prime_wlan_controller import (
    AlarmStatus,
    check_wlan_controller_access_points,
    check_wlan_controller_alarm_status,
    check_wlan_controller_clients,
    check_wlan_controller_last_backup,
    check_wlan_controller_metadata,
    check_wlan_controller_reachability,
    DAY_IN_SECONDS,
    discovery_wlan_controller,
    get_controllers,
    get_last_backup,
    parse_cisco_prime_wlan_controller,
    WlanController,
)

WLAN_CONTROLLERS = {
    "queryResponse": {
        "@last": 13,
        "@first": 0,
        "@count": 14,
        "@type": "WlanControllers",
        "@domain": "ROOT-DOMAIN",
        "@requestUrl": "https://prime.rz.uni-leipzig.de/webacs/api/v4/data/WlanControllers?.full=true",
        "@responseType": "listEntityInstances",
        "@rootUrl": "https://prime.rz.uni-leipzig.de/webacs/api/v4/data",
        "entity": [
            {
                "@dtoType": "wlanControllersDTO",
                "@type": "WlanControllers",
                "@url": "https://prime.rz.uni-leipzig.de/webacs/api/v4/data/WlanControllers/27017138148",
                "wlanControllersDTO": {
                    "@displayName": "27017138148",
                    "@id": 27017138148,
                    "alarmStatus": "CRITICAL",
                    "apCount": 483,
                    "auditStatus": "MISMATCH",
                    "autoRefresh": False,
                    "clientCount": 167,
                    "contact": "E.Friedrich 33423",
                    "ipAddress": "10.5.1.11",
                    "lastBackup": "2020-07-27T17:28:02.000Z",
                    "location": "secgate 1:1",
                    "mobilityGroupName": "mobile-01",
                    "name": "wism21",
                    "reachabilityStatus": True,
                    "rfGroupName": "mobile-01",
                    "softwareVersion": "8.0.152.12",
                    "type": "Cisco WiSM2 Controller",
                },
            },
            {
                "@dtoType": "wlanControllersDTO",
                "@type": "WlanControllers",
                "@url": "https://prime.rz.uni-leipzig.de/webacs/api/v4/data/WlanControllers/27369977635",
                "wlanControllersDTO": {
                    "@displayName": "27369977635",
                    "@id": 27369977635,
                    "alarmStatus": "CRITICAL",
                    "apCount": 298,
                    "auditStatus": "MISMATCH",
                    "autoRefresh": False,
                    "clientCount": 108,
                    "contact": "E.Friedrich 33423",
                    "ipAddress": "10.5.1.8",
                    "location": "secgate 1:1",
                    "mobilityGroupName": "mobile-02",
                    "name": "wism22",
                    "reachabilityStatus": False,
                    "rfGroupName": "mobile-02",
                    "softwareVersion": "8.0.152.12",
                    "type": "Cisco WiSM2 Controller",
                },
            },
        ],
    }
}

WLAN_CONTROLLERS_SECTION = {
    "wism21": WlanController(
        name="wism21",
        type="Cisco WiSM2 Controller",
        software_version="8.0.152.12",
        ip_address="10.5.1.11",
        location="secgate 1:1",
        group_name="mobile-01",
        mobility_group_name="mobile-01",
        alarm_status=AlarmStatus.CRITICAL,
        access_points_count=483,
        client_count=167,
        reachability_status=True,
        last_backup=datetime(2020, 7, 27, 17, 28, 2, tzinfo=UTC),
    ),
    "wism22": WlanController(
        name="wism22",
        type="Cisco WiSM2 Controller",
        software_version="8.0.152.12",
        ip_address="10.5.1.8",
        location="secgate 1:1",
        group_name="mobile-02",
        mobility_group_name="mobile-02",
        alarm_status=AlarmStatus.CRITICAL,
        access_points_count=298,
        client_count=108,
        reachability_status=False,
        last_backup=None,
    ),
}


@pytest.mark.parametrize(
    "controller_data, expected_result",
    [
        (
            WLAN_CONTROLLERS,
            [
                {
                    "@displayName": "27017138148",
                    "@id": 27017138148,
                    "alarmStatus": "CRITICAL",
                    "apCount": 483,
                    "auditStatus": "MISMATCH",
                    "autoRefresh": False,
                    "clientCount": 167,
                    "contact": "E.Friedrich 33423",
                    "ipAddress": "10.5.1.11",
                    "lastBackup": "2020-07-27T17:28:02.000Z",
                    "location": "secgate 1:1",
                    "mobilityGroupName": "mobile-01",
                    "name": "wism21",
                    "reachabilityStatus": True,
                    "rfGroupName": "mobile-01",
                    "softwareVersion": "8.0.152.12",
                    "type": "Cisco WiSM2 Controller",
                },
                {
                    "@displayName": "27369977635",
                    "@id": 27369977635,
                    "alarmStatus": "CRITICAL",
                    "apCount": 298,
                    "auditStatus": "MISMATCH",
                    "autoRefresh": False,
                    "clientCount": 108,
                    "contact": "E.Friedrich 33423",
                    "ipAddress": "10.5.1.8",
                    "location": "secgate 1:1",
                    "mobilityGroupName": "mobile-02",
                    "name": "wism22",
                    "reachabilityStatus": False,
                    "rfGroupName": "mobile-02",
                    "softwareVersion": "8.0.152.12",
                    "type": "Cisco WiSM2 Controller",
                },
            ],
        )
    ],
)
def test_get_controllers(
    controller_data: dict[str, Any], expected_result: list[dict[str, Any]]
) -> None:
    controllers = get_controllers(controller_data)
    assert list(controllers) == expected_result


@pytest.mark.parametrize(
    "last_backup, expected_result",
    [
        (None, None),
        ("2020-07-27T17:27:39.000Z", datetime(2020, 7, 27, 17, 27, 39, tzinfo=UTC)),
    ],
)
def test_get_last_backup(last_backup: str | None, expected_result: datetime | None) -> None:
    assert get_last_backup(last_backup) == expected_result


@pytest.mark.parametrize(
    "controller_data, expected_result",
    [(WLAN_CONTROLLERS, WLAN_CONTROLLERS_SECTION)],
)
def test_parse_cisco_prime_wlan_controller(
    controller_data: dict[str, Any], expected_result: dict[str, WlanController]
) -> None:
    string_table = [[json.dumps(controller_data)]]
    assert parse_cisco_prime_wlan_controller(string_table) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [(WLAN_CONTROLLERS_SECTION, [Service(item="wism21"), Service(item="wism22")])],
)
def test_discovery_wlan_controller(
    section: dict[str, WlanController], expected_result: list[Service]
) -> None:
    services = discovery_wlan_controller(section)

    assert list(services) == expected_result


@pytest.mark.parametrize(
    "item, section, expected_result",
    [
        (
            "wism21",
            WLAN_CONTROLLERS_SECTION,
            [
                Result(state=State.OK, notice="Name: wism21"),
                Result(state=State.OK, summary="Type: Cisco WiSM2 Controller"),
                Result(state=State.OK, summary="Software version: 8.0.152.12"),
                Result(state=State.OK, notice="IP address: 10.5.1.11"),
                Result(state=State.OK, summary="Location: secgate 1:1"),
                Result(state=State.OK, summary="Group name: mobile-01"),
                Result(state=State.OK, summary="Mobility group name: mobile-01"),
            ],
        ),
        ("wism23", WLAN_CONTROLLERS_SECTION, []),
    ],
)
def test_check_wlan_controller_metadata(
    item: str, section: dict[str, WlanController], expected_result: list[CheckResult]
) -> None:
    result = check_wlan_controller_metadata(item, section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, section, expected_result",
    [
        (
            "wism21",
            WLAN_CONTROLLERS_SECTION,
            [Result(state=State.CRIT, summary="CRITICAL")],
        ),
        ("wism23", WLAN_CONTROLLERS_SECTION, []),
    ],
)
def test_check_wlan_controller_alarm_status(
    item: str, section: dict[str, WlanController], expected_result: list[CheckResult]
) -> None:
    result = check_wlan_controller_alarm_status(item, section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "wism21",
            {"access_points": ("fixed", (300, 500))},
            WLAN_CONTROLLERS_SECTION,
            [
                Result(state=State.WARN, summary="Count: 483 (warn/crit at 300/500)"),
                Metric("ap_count", 483.0, levels=(300.0, 500.0)),
            ],
        ),
        ("wism23", {"access_points": (300, 500)}, WLAN_CONTROLLERS_SECTION, []),
    ],
)
def test_check_wlan_controller_access_points(
    item: str,
    params: Mapping[str, tuple[Literal["fixed"], tuple[float, float]]],
    section: dict[str, WlanController],
    expected_result: list[CheckResult],
) -> None:
    result = check_wlan_controller_access_points(item, params, section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "wism21",
            {"clients": ("fixed", (50, 100))},
            WLAN_CONTROLLERS_SECTION,
            [
                Result(state=State.CRIT, summary="Count: 167 (warn/crit at 50/100)"),
                Metric("clients_count", 167.0, levels=(50.0, 100.0)),
            ],
        ),
        ("wism23", {}, WLAN_CONTROLLERS_SECTION, []),
    ],
)
def test_check_wlan_controller_clients(
    item: str,
    params: Mapping[str, tuple[Literal["fixed"], tuple[float, float]]],
    section: dict[str, WlanController],
    expected_result: list[CheckResult],
) -> None:
    result = check_wlan_controller_clients(item, params, section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, section, expected_result",
    [
        (
            "wism21",
            WLAN_CONTROLLERS_SECTION,
            [Result(state=State.OK, summary="REACHABLE")],
        ),
        (
            "wism22",
            WLAN_CONTROLLERS_SECTION,
            [Result(state=State.CRIT, summary="UNREACHABLE")],
        ),
        ("wism23", WLAN_CONTROLLERS_SECTION, []),
    ],
)
def test_check_wlan_controller_reachability(
    item: str, section: dict[str, WlanController], expected_result: list[CheckResult]
) -> None:
    result = check_wlan_controller_reachability(item, section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "wism21",
            {"last_backup": ("fixed", (100 * DAY_IN_SECONDS, 600 * DAY_IN_SECONDS))},
            WLAN_CONTROLLERS_SECTION,
            [
                Result(
                    state=State.WARN,
                    summary="1 year 91 days (warn/crit at 100 days 0 hours/1 year 235 days)",
                ),
                Metric("backup_age", 39421918.0, levels=(8640000.0, 51840000.0)),
            ],
        ),
        (
            "wism22",
            {},
            WLAN_CONTROLLERS_SECTION,
            [Result(state=State.WARN, summary="No backup")],
        ),
        ("wism23", {}, WLAN_CONTROLLERS_SECTION, []),
    ],
)
@time_machine.travel(datetime.fromisoformat("2021-10-27 00:00:00.000000Z"))
def test_check_wlan_controller_last_backup(
    item: str,
    params: Mapping[str, tuple[Literal["fixed"], tuple[float, float]]],
    section: dict[str, WlanController],
    expected_result: list[CheckResult],
) -> None:
    result = check_wlan_controller_last_backup(item, params, section)
    assert list(result) == expected_result
