#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    Attributes,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.fritzbox.agent_based.fritz import (
    check_fritz_conn,
    check_fritz_link,
    check_fritz_uptime,
    check_fritz_wan_if,
    discover_fritz_conn,
    discover_fritz_link,
    discover_fritz_uptime,
    discover_fritz_wan_if,
    inventory_fritz,
    parse_fritz,
    Section,
)
from cmk.plugins.lib.interfaces import CHECK_DEFAULT_PARAMETERS, DISCOVERY_DEFAULT_PARAMETERS

_STRING_TABLE = [
    ["VersionOS", "137.06.83"],
    ["VersionDevice", "AVM", "FRITZ!Box", "7412", "(UI)"],
    ["NewVoipDNSServer1", "217.237.148.102"],
    ["NewDNSServer2", "217.237.151.115"],
    ["NewDNSServer1", "217.237.148.102"],
    ["NewVoipDNSServer2", "217.237.151.115"],
    ["NewIdleDisconnectTime", "0"],
    ["NewLayer1DownstreamMaxBitRate", "25088000"],
    ["NewWANAccessType", "DSL"],
    ["NewByteSendRate", "197"],
    ["NewPacketReceiveRate", "0"],
    ["NewConnectionStatus", "Connected"],
    ["NewRoutedBridgedModeBoth", "1"],
    ["NewUptime", "1"],
    ["NewTotalBytesReceived", "178074787"],
    ["NewPacketSendRate", "0"],
    ["NewPhysicalLinkStatus", "Up"],
    ["NewLinkStatus", "Up"],
    ["NewLayer1UpstreamMaxBitRate", "5056000"],
    ["NewTotalBytesSent", "40948982"],
    ["NewLastConnectionError", "ERROR_NONE"],
    ["NewAutoDisconnectTime", "0"],
    ["NewExternalIPAddress", "217.235.84.223"],
    ["NewLinkType", "PPPoE"],
    ["NewByteReceiveRate", "0"],
    ["NewUpnpControlEnabled", "1"],
]

_SECTION = {
    "NewAutoDisconnectTime": "0",
    "NewByteReceiveRate": "0",
    "NewByteSendRate": "197",
    "NewConnectionStatus": "Connected",
    "NewDNSServer1": "217.237.148.102",
    "NewDNSServer2": "217.237.151.115",
    "NewExternalIPAddress": "217.235.84.223",
    "NewIdleDisconnectTime": "0",
    "NewLastConnectionError": "ERROR_NONE",
    "NewLayer1DownstreamMaxBitRate": "25088000",
    "NewLayer1UpstreamMaxBitRate": "5056000",
    "NewLinkStatus": "Up",
    "NewLinkType": "PPPoE",
    "NewPacketReceiveRate": "0",
    "NewPacketSendRate": "0",
    "NewPhysicalLinkStatus": "Up",
    "NewRoutedBridgedModeBoth": "1",
    "NewTotalBytesReceived": "178074787",
    "NewTotalBytesSent": "40948982",
    "NewUpnpControlEnabled": "1",
    "NewUptime": "1",
    "NewVoipDNSServer1": "217.237.148.102",
    "NewVoipDNSServer2": "217.237.151.115",
    "NewWANAccessType": "DSL",
    "VersionDevice": "AVM FRITZ!Box 7412 (UI)",
    "VersionOS": "137.06.83",
}


def test_parse_fritz() -> None:
    assert parse_fritz(_STRING_TABLE) == _SECTION


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [
                Service(
                    item="0",
                    parameters={
                        "item_appearance": "index",
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 25088000,
                    },
                ),
            ],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_discover_fritz_wan_if(
    section: Section,
    expected_result: DiscoveryResult,
) -> None:
    assert (
        list(
            discover_fritz_wan_if(
                [DISCOVERY_DEFAULT_PARAMETERS],
                section,
            )
        )
        == expected_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [
                Result(
                    state=State.OK,
                    summary="[WAN]",
                ),
                Result(
                    state=State.OK,
                    summary="(up)",
                    details="Operational state: up",
                ),
                Result(
                    state=State.OK,
                    summary="Speed: 25.1 MBit/s",
                ),
                Result(
                    state=State.OK,
                    notice=(
                        "Could not compute rates for the following counter(s):\n"
                        "in_octets: Counter 'in_octets.0.WAN.WAN.None' has been initialized."
                        " Result available on second check execution.\n"
                        "out_octets: Counter 'out_octets.0.WAN.WAN.None' has been initialized."
                        " Result available on second check execution."
                    ),
                ),
            ],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty section",
        ),
    ],
)
def test_check_fritz_wan_if(
    section: Section,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_fritz_wan_if(
                "0",
                CHECK_DEFAULT_PARAMETERS,
                section,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [Service()],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_discover_fritz_conn(
    section: Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(discover_fritz_conn(section)) == expected_result


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [
                Result(
                    state=State.OK,
                    summary="Connection status: Connected",
                ),
                Result(
                    state=State.OK,
                    summary="WAN IP Address: 217.235.84.223",
                ),
            ],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_check_fritz_conn(
    section: Section,
    expected_result: CheckResult,
) -> None:
    assert list(check_fritz_conn(section)) == expected_result


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [Service()],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_discover_fritz_uptime(
    section: Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(discover_fritz_uptime(section)) == expected_result


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [
                Result(
                    state=State.OK,
                    summary="Up since 2022-03-17 11:07:38",
                ),
                Result(
                    state=State.OK,
                    summary="Uptime: 1 second",
                ),
                Metric(
                    "uptime",
                    1.0,
                ),
            ],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_check_fritz_uptime(
    section: Section,
    expected_result: CheckResult,
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1647515259, tz=ZoneInfo("UTC"))):
        assert (
            list(
                check_fritz_uptime(
                    {},
                    section,
                )
            )
            == expected_result
        )


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [Service()],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_discover_fritz_link(
    section: Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(discover_fritz_link(section)) == expected_result


@pytest.mark.parametrize(
    [
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTION,
            [
                Result(
                    state=State.OK,
                    summary="Link status: Up",
                ),
                Result(
                    state=State.OK,
                    summary="Physical link status: Up",
                ),
            ],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty data",
        ),
    ],
)
def test_check_fritz_link(
    section: Section,
    expected_result: CheckResult,
) -> None:
    assert list(check_fritz_link(section)) == expected_result


def test_inventory_fritz() -> None:
    assert list(inventory_fritz(_SECTION)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={"model": "AVM FRITZ!Box 7412 (UI)"},
        ),
        Attributes(
            path=["software", "os"],
            inventory_attributes={"version": "137.06.83"},
        ),
        Attributes(
            path=["software", "applications", "fritz"],
            inventory_attributes={
                "link_type": "PPPoE",
                "wan_access_type": "DSL",
                "auto_disconnect_time": "0",
                "dns_server_1": "217.237.148.102",
                "dns_server_2": "217.237.151.115",
                "voip_dns_server_1": "217.237.148.102",
                "voip_dns_server_2": "217.237.151.115",
                "upnp_config_enabled": "1",
            },
        ),
    ]
