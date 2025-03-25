#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from pathlib import Path

import pytest

from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.cisco_wlc_clients import (
    parse_cisco_wlc_9800_clients,
    parse_cisco_wlc_clients,
    snmp_section_cisco_wlc_9800_clients,
)
from cmk.plugins.collection.agent_based.wlc_clients import (
    check_plugin_wlc_clients,
    check_wlc_clients,
)
from cmk.plugins.lib.wlc_clients import (
    ClientsPerInterface,
    ClientsTotal,
    VsResult,
    WlcClientsSection,
)

# raw data looks like this:
# TODO: we sould use this as test input
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssSsid
# .1.3.6.1.4.1.14179.2.1.1.1.2.2 corp_internal_001
# .1.3.6.1.4.1.14179.2.1.1.1.2.3 corp_internal_003
# .1.3.6.1.4.1.14179.2.1.1.1.2.19 AnotherWifiSSID
# .1.3.6.1.4.1.14179.2.1.1.1.2.31 FreePublicWifi
# .1.3.6.1.4.1.14179.2.1.1.1.2.32 FreePublicWifi
# .1.3.6.1.4.1.14179.2.1.1.1.2.33 FreePublicWifi
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssInterfaceName
# .1.3.6.1.4.1.14179.2.1.1.1.42.2 corp_intern_001
# .1.3.6.1.4.1.14179.2.1.1.1.42.3 corp_intern_003
# .1.3.6.1.4.1.14179.2.1.1.1.42.19 interface_name
# .1.3.6.1.4.1.14179.2.1.1.1.42.31 guest1
# .1.3.6.1.4.1.14179.2.1.1.1.42.32 guest2
# .1.3.6.1.4.1.14179.2.1.1.1.42.33 guest3
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssNumberOfMobileStations
# .1.3.6.1.4.1.14179.2.1.1.1.38.2 1
# .1.3.6.1.4.1.14179.2.1.1.1.38.3 3
# .1.3.6.1.4.1.14179.2.1.1.1.38.19 0
# .1.3.6.1.4.1.14179.2.1.1.1.38.31 0
# .1.3.6.1.4.1.14179.2.1.1.1.38.32 114
# .1.3.6.1.4.1.14179.2.1.1.1.38.33 68

# or for 9800 like this:
# ## CISCO-LWAPP-WLAN-MIB::cLWlanSsid
# .1.3.6.1.4.1.9.9.512.1.1.1.1.4.1 guest
# .1.3.6.1.4.1.9.9.512.1.1.1.1.4.2 free
# .1.3.6.1.4.1.9.9.512.1.1.1.1.4.4 mobile
# .1.3.6.1.4.1.9.9.512.1.1.1.1.4.5 internal
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssNumberOfMobileStations
# .1.3.6.1.4.1.14179.2.1.1.1.38.1 9
# .1.3.6.1.4.1.14179.2.1.1.1.38.2 8
# .1.3.6.1.4.1.14179.2.1.1.1.38.4 6
# .1.3.6.1.4.1.14179.2.1.1.1.38.5 5

INFO = [
    [
        ["corp_internal_001", "corp_intern_001", "1"],
        ["corp_internal_003", "corp_intern_003", "3"],
        ["AnotherWifiSSID", "interface_name", "0"],
        ["FreePublicWifi", "guest1", "0"],
        ["FreePublicWifi", "guest2", "114"],
        ["FreePublicWifi", "guest3", "68"],
    ]
]

ITEM_RESULT = [
    [
        "Summary",
        [
            Result(state=State.OK, summary="Connections: 186"),
            Metric("connections", 186.0),
        ],
    ],
    [
        "corp_internal_003",
        [
            Result(state=State.OK, summary="Connections: 3"),
            Metric("connections", 3.0),
            Result(state=State.OK, summary="(corp_intern_003: 3)"),
        ],
    ],
    [
        "FreePublicWifi",
        [
            Result(state=State.OK, summary="Connections: 182"),
            Metric("connections", 182.0),
            Result(state=State.OK, summary="(guest1: 0, guest2: 114, guest3: 68)"),
        ],
    ],
]


def _run_parse_and_check(
    item: str,
    info: list[StringTable],
    params: VsResult | None = None,
) -> CheckResult:
    if params is None:
        params = {}
    yield from check_wlc_clients(
        item=item,
        params=params,
        section=parse_cisco_wlc_clients(info),
    )


@pytest.mark.parametrize("item, result", ITEM_RESULT)
def test_cisco_wlc_clients(item: str, result: CheckResult) -> None:
    assert list(_run_parse_and_check(item, INFO)) == result


PARAM_STATUS = [
    # summary: 186 connections
    [{}, State.OK],
    [{"levels": (300, 400)}, State.OK],
    [{"levels": (100, 400)}, State.WARN],
    [{"levels": (50, 100)}, State.CRIT],
    [{"levels_lower": (100, 50)}, State.OK],
    [{"levels_lower": (200, 100)}, State.WARN],
    [{"levels_lower": (300, 200)}, State.CRIT],
    # check status when exactly on the defined level
    [{"levels": (186, 400)}, State.WARN],
    [{"levels": (50, 186)}, State.CRIT],
    [{"levels_lower": (186, 100)}, State.OK],
    [{"levels_lower": (300, 186)}, State.WARN],
]


@pytest.mark.parametrize("param, status", PARAM_STATUS)
def test_cisco_wlc_clients_parameter(param: VsResult | None, status: State) -> None:
    result = next(iter(_run_parse_and_check("Summary", INFO, param)))
    assert isinstance(result, Result)
    assert result.state == status


def test_parse_cisco_wlc_clients() -> None:
    result = parse_cisco_wlc_clients(INFO)

    assert result == WlcClientsSection(
        total_clients=186,
        clients_per_ssid={
            "FreePublicWifi": ClientsPerInterface(
                per_interface={
                    "guest1": 0,
                    "guest2": 114,
                    "guest3": 68,
                }
            ),
            "AnotherWifiSSID": ClientsPerInterface(per_interface={"interface_name": 0}),
            "corp_internal_001": ClientsPerInterface(per_interface={"corp_intern_001": 1}),
            "corp_internal_003": ClientsPerInterface(per_interface={"corp_intern_003": 3}),
        },
    )


INFO_9800 = [
    [
        ["guest"],
        ["guest"],
        ["mobile"],
        ["internal"],
    ],
    [
        ["9"],
        ["8"],
        ["6"],
        ["5"],
    ],
]


def test_parse_cisco_wlc_9800_clients() -> None:
    result = parse_cisco_wlc_9800_clients(INFO_9800)

    assert result == WlcClientsSection(
        total_clients=9 + 8 + 6 + 5,
        clients_per_ssid={
            "guest": ClientsTotal(total=9 + 8),
            "mobile": ClientsTotal(total=6),
            "internal": ClientsTotal(total=5),
        },
    )


DATA = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.9.1.2861
.1.3.6.1.4.1.9.9.512.1.1.1.1.4.1 WLAN
.1.3.6.1.4.1.9.9.512.1.1.1.1.4.10 PHONES
.1.3.6.1.4.1.9.9.512.1.1.1.1.4.999 GuestLAN
.1.3.6.1.4.1.14179.2.1.1.1.38.1 13
.1.3.6.1.4.1.14179.2.1.1.1.38.10 0
.1.3.6.1.4.1.14179.2.1.1.1.38.999 17
"""


def test_cisco_wlc_client_with_snmp_walk(as_path: Callable[[str], Path]) -> None:
    # test detect
    assert snmp_is_detected(snmp_section_cisco_wlc_9800_clients, as_path(DATA))

    # parse
    parsed = get_parsed_snmp_section(snmp_section_cisco_wlc_9800_clients, as_path(DATA))

    # test discovery
    assert list(check_plugin_wlc_clients.discovery_function(parsed)) == [
        Service(item="Summary"),
        Service(item="WLAN"),
        Service(item="PHONES"),
        Service(item="GuestLAN"),
    ]

    # test check
    assert list(check_plugin_wlc_clients.check_function("WLAN", {}, parsed)) == [
        Result(state=State.OK, summary="Connections: 13"),
        Metric("connections", 13.0),
    ]
