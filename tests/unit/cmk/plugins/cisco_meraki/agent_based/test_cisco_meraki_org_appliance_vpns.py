#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_appliance_vpns import (
    check_appliance_vpns,
    CheckParams,
    discover_appliance_vpns,
    parse_appliance_vpns,
)
from cmk.plugins.cisco_meraki.lib.schema import RawUplinkVpnStatuses


class _RawUplinkVpnStatuses(TypedDictFactory[RawUplinkVpnStatuses]):
    __check_model__ = False

    @classmethod
    def networkName(cls) -> str:
        return "main"

    @classmethod
    def vpnMode(cls) -> str:
        return "hub"

    @classmethod
    def uplinks(cls) -> list[dict[str, str]]:
        return [{"interface": "wan1", "publicIp": "1.2.3.4"}]


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_appliance_uplinks_no_payload(string_table: StringTable) -> None:
    section = parse_appliance_vpns(string_table)
    assert not list(discover_appliance_vpns(section))


def test_discover_appliance_uplinks() -> None:
    uplinks = _RawUplinkVpnStatuses.build(networkName="main")
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_vpns(string_table)

    value = list(discover_appliance_vpns(section))
    expected = [Service(item="main")]

    assert value == expected


@pytest.fixture
def params() -> CheckParams:
    return CheckParams(status_not_reachable=1)


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_appliance_uplinks_no_payload(string_table: StringTable, params: CheckParams) -> None:
    section = parse_appliance_vpns(string_table)
    assert not list(check_appliance_vpns("", params, section))


def test_check_appliance_uplinks(params: CheckParams) -> None:
    uplinks = _RawUplinkVpnStatuses.build(
        merakiVpnPeers=[
            {
                "networkName": "main",
                "reachability": "reachable",
            }
        ],
    )
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_vpns(string_table)

    value = list(check_appliance_vpns("main", params, section))
    expected = [
        Result(state=State.OK, summary="Status: reachable"),
        Result(state=State.OK, summary="Type: Meraki VPN peer"),
        Result(state=State.OK, summary="Peer IP: n/a"),
        Result(state=State.OK, notice="VPN mode: hub"),
        Result(state=State.OK, notice="Uplink(s):"),
        Result(state=State.OK, notice="Name: wan1, Public IP: 1.2.3.4"),
    ]

    assert value == expected


def test_check_appliance_vpns_third_party(params: CheckParams) -> None:
    vpn_status = _RawUplinkVpnStatuses.build(
        thirdPartyVpnPeers=[
            {
                "name": "main",
                "publicIp": "1.2.3.5",
                "reachability": "reachable",
            }
        ],
    )
    string_table = [[f"[{json.dumps(vpn_status)}]"]]
    section = parse_appliance_vpns(string_table)

    value = list(check_appliance_vpns("main", params, section))
    expected = [
        Result(state=State.OK, summary="Status: reachable"),
        Result(state=State.OK, summary="Type: Third party VPN peer"),
        Result(state=State.OK, summary="Peer IP: 1.2.3.5"),
        Result(state=State.OK, notice="VPN mode: hub"),
        Result(state=State.OK, notice="Uplink(s):"),
        Result(state=State.OK, notice="Name: wan1, Public IP: 1.2.3.4"),
    ]

    assert value == expected


def test_check_appliance_vpns_unreachable_status(params: CheckParams) -> None:
    vpn_status = _RawUplinkVpnStatuses.build(
        thirdPartyVpnPeers=[
            {
                "name": "main",
                "reachability": "unreachable",
            }
        ]
    )
    string_table = [[f"[{json.dumps(vpn_status)}]"]]
    section = parse_appliance_vpns(string_table)

    value, *_ = list(check_appliance_vpns("main", params, section))
    expected = Result(state=State.WARN, summary="Status: unreachable")

    assert value == expected


def test_check_random_peer_data(params: CheckParams) -> None:
    vpn_status = _RawUplinkVpnStatuses.build()
    string_table = [[f"[{json.dumps(vpn_status)}]"]]
    section = parse_appliance_vpns(string_table)

    value = list(check_appliance_vpns("main", params, section))
    expected = [
        Result(state=State.WARN, summary="Status: n/a"),
        Result(state=State.OK, summary="Type: n/a"),
        Result(state=State.OK, summary="Peer IP: n/a"),
        Result(state=State.OK, notice="VPN mode: hub"),
        Result(state=State.OK, notice="Uplink(s):"),
        Result(state=State.OK, notice="Name: wan1, Public IP: 1.2.3.4"),
    ]

    assert value == expected
