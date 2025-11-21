#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_appliance_uplinks import (
    check_appliance_uplinks,
    CheckParams,
    discover_appliance_uplinks,
    parse_appliance_uplinks,
)
from cmk.plugins.cisco_meraki.lib.schema import UplinkStatuses


class _UplinkStatusesFactory(TypedDictFactory[UplinkStatuses]):
    __check_model__ = False

    @classmethod
    def uplinks(cls) -> list[dict[str, object]]:
        return [
            {
                "interface": "wan1",
                "status": "active",
                "ip": "1.2.3.4",
                "gateway": "1.2.3.5",
                "publicIp": "192.0.2.2",
                "primaryDns": "8.8.8.8",
                "secondaryDns": "8.8.4.4",
                "ipAssignedBy": "static",
            }
        ]

    @classmethod
    def lastReportedAt(cls) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d")


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_appliance_uplinks_no_payload(string_table: StringTable) -> None:
    section = parse_appliance_uplinks(string_table)
    assert not list(discover_appliance_uplinks(section))


def test_discover_appliance_uplinks() -> None:
    uplinks = _UplinkStatusesFactory.build()
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_uplinks(string_table)

    value = list(discover_appliance_uplinks(section))
    expected = [Service(item="wan1")]

    assert value == expected


@pytest.fixture
def params() -> CheckParams:
    return CheckParams(
        status_map={"active": 0, "ready": 0, "connecting": 1, "not_connected": 1, "failed": 2},
        show_traffic=True,
    )


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_appliance_uplinks_no_payload(string_table: StringTable, params: CheckParams) -> None:
    section = parse_appliance_uplinks(string_table)
    assert not list(check_appliance_uplinks("", params, section))


def test_check_appliance_uplinks(params: CheckParams) -> None:
    uplinks = _UplinkStatusesFactory.build(
        networkName="main",
        highAvailability={"enabled": "true", "role": "primary"},
        usageByInterface={"wan1": {"received": 200, "sent": 100}},
    )
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_uplinks(string_table)

    value = list(check_appliance_uplinks("wan1", params, section))
    expected = [
        Result(state=State.OK, summary="Status: active"),
        Result(state=State.OK, summary="IP: 1.2.3.4"),
        Result(state=State.OK, summary="Public IP: 192.0.2.2"),
        Result(state=State.OK, notice="Network: main"),
        Result(state=State.OK, summary="In: 26.7 Bit/s"),
        Metric("if_in_bps", 26.666666666666668),
        Result(state=State.OK, summary="Out: 13.3 Bit/s"),
        Metric("if_out_bps", 13.333333333333334),
        Result(state=State.OK, notice="H/A enabled: True"),
        Result(state=State.OK, notice="H/A role: primary"),
        Result(state=State.OK, notice="Gateway: 1.2.3.5"),
        Result(state=State.OK, notice="IP assigned by: static"),
        Result(state=State.OK, notice="Primary DNS: 8.8.8.8"),
        Result(state=State.OK, notice="Secondary DNS: 8.8.4.4"),
    ]

    assert value == expected


def test_check_appliance_uplinks_zero_usage(params: CheckParams) -> None:
    uplinks = _UplinkStatusesFactory.build(usageByInterface={"wan1": {"received": 0, "sent": 0}})
    string_table = [[f"[{json.dumps(uplinks)}]"]]
    section = parse_appliance_uplinks(string_table)

    value = set(check_appliance_uplinks("wan1", params, section))
    expected = {
        Result(state=State.OK, summary="In: 0.00 Bit/s"),
        Metric("if_in_bps", 0.0),
        Result(state=State.OK, summary="Out: 0.00 Bit/s"),
        Metric("if_out_bps", 0.0),
    }

    assert expected & value == expected
