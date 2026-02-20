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


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_appliance_uplinks_no_payload(string_table: StringTable) -> None:
    section = parse_appliance_vpns(string_table)
    assert not list(discover_appliance_vpns(section))


def test_discover_appliance_uplinks() -> None:
    uplinks = _RawUplinkVpnStatuses.build(
        merakiVpnPeers=[{"networkName": "main"}, {"networkName": "secondary"}],
        thirdPartyVpnPeers=[{"name": "third-party-vpn"}],
    )
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_vpns(string_table)

    value = list(discover_appliance_vpns(section))
    expected = [
        Service(item="main"),
        Service(item="secondary"),
        Service(item="third-party-vpn"),
    ]

    assert value == expected


@pytest.fixture
def params() -> CheckParams:
    return CheckParams(status_not_reachable=State.WARN.value)


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_appliance_uplinks_no_payload(string_table: StringTable, params: CheckParams) -> None:
    section = parse_appliance_vpns(string_table)
    assert not list(check_appliance_vpns("", params, section))


def test_check_appliance_vpns_meraki(params: CheckParams) -> None:
    uplinks = _RawUplinkVpnStatuses.build(
        merakiVpnPeers=[
            {
                "networkName": "main",
                "networkId": "L_123",
                "reachability": "reachable",
            }
        ],
    )
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_vpns(string_table)

    value = list(check_appliance_vpns("main", params, section))
    expected = [
        Result(state=State.OK, summary="Reachability: reachable"),
        Result(state=State.OK, summary="Type: Meraki VPN peer"),
        Result(state=State.OK, notice="Network ID: L_123"),
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
        Result(state=State.OK, summary="Reachability: reachable"),
        Result(state=State.OK, summary="Type: Third party VPN peer"),
        Result(state=State.OK, notice="Public IP: 1.2.3.5"),
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
    expected = Result(state=State.WARN, summary="Reachability: unreachable")

    assert value == expected
