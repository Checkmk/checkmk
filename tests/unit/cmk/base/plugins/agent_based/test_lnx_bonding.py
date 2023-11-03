#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from typing_extensions import Literal, TypedDict

from cmk.base.plugins.agent_based import lnx_bonding
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.bonding import check_bonding

from cmk.plugins.lib import bonding

DATA_FAILOVER = [
    ["==> ./bond0 <=="],
    ["Ethernet Channel Bonding Driver", " v5.13.19-5-pve"],
    #
    ["Bonding Mode", " fault-tolerance (active-backup)"],
    ["Primary Slave", " None"],
    ["Currently Active Slave", " enp129s0f2"],
    ["MII Status", " up"],
    ["MII Polling Interval (ms)", " 100"],
    ["Up Delay (ms)", " 200"],
    ["Down Delay (ms)", " 200"],
    ["Peer Notification Delay (ms)", " 0"],
    #
    ["Slave Interface", " enp129s0f2"],
    ["MII Status", " up"],
    ["Speed", " 10000 Mbps"],
    ["Duplex", " full"],
    ["Link Failure Count", " 0"],
    ["Permanent HW addr", " 3c", "ec", "ef", "28", "4a", "56"],
    ["Slave queue ID", " 0"],
    #
    ["Slave Interface", " enp129s0f3"],
    ["MII Status", " up"],
    ["Speed", " 10000 Mbps"],
    ["Duplex", " full"],
    ["Link Failure Count", " 0"],
    ["Permanent HW addr", " 3c", "ec", "ef", "28", "4a", "57"],
    ["Slave queue ID", " 0"],
]


def test_parse_failover() -> None:
    assert lnx_bonding.parse_lnx_bonding(DATA_FAILOVER) == {
        "bond0": {
            "active": "enp129s0f2",
            "interfaces": {
                "enp129s0f2": {"failures": 0, "hwaddr": "3C:EC:EF:28:4A:56", "status": "up"},
                "enp129s0f3": {"failures": 0, "hwaddr": "3C:EC:EF:28:4A:57", "status": "up"},
            },
            "mode": "fault-tolerance (active-backup)",
            "primary": "None",
            "status": "up",
        },
    }


mode_option = Literal[
    "balance-rr",
    "active-backup",
    "balance-xor",
    "broadcast",
    "802.3ad",
    "balance-tlb",
    "balance-alb",
]


test_param_type = tuple[mode_option, Literal[0, 1, 2, 3]]


class Params(TypedDict):
    expect_active: str
    ieee_302_3ad_agg_id_missmatch_state: int
    expected_bonding_mode_and_state: test_param_type


not_expected_modes = [
    ("balance-rr", 0),
    ("balance-xor", 1),
    ("broadcast", 2),
    ("802.3ad", 3),
    ("balance-tlb", 0),
    ("balance-alb", 1),
]


@pytest.fixture(name="params")
def default_params() -> Params:
    params: Params = {
        "expect_active": "ignore",
        "ieee_302_3ad_agg_id_missmatch_state": 1,
        "expected_bonding_mode_and_state": ("active-backup", 1),
    }
    return params


@pytest.mark.parametrize("mode", not_expected_modes)
def test_mode_not_as_expected(mode: test_param_type, params: Params) -> None:
    params["expected_bonding_mode_and_state"] = mode
    section: bonding.Section = lnx_bonding.parse_lnx_bonding(DATA_FAILOVER)
    check_result = list(check_bonding(item="bond0", params=params, section=section))
    assert check_result[1] == Result(
        state=State(mode[1]), summary=f"Mode: active-backup (expected mode: {mode[0]})"
    )


def test_mode_as_expected(params: Params) -> None:
    section: bonding.Section = lnx_bonding.parse_lnx_bonding(DATA_FAILOVER)
    check_result = list(check_bonding(item="bond0", params=params, section=section))
    assert check_result[1] == Result(state=State(0), summary="Mode: active-backup")
