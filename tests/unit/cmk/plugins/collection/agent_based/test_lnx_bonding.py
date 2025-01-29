#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import TypedDict

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based import lnx_bonding
from cmk.plugins.collection.agent_based.bonding import check_bonding
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


class BondingModeConfig(TypedDict):
    mode_0: int
    mode_1: int
    mode_2: int
    mode_3: int
    mode_4: int
    mode_5: int
    mode_6: int


class Params(TypedDict):
    expect_active: str
    ieee_302_3ad_agg_id_missmatch_state: int
    bonding_mode_states: BondingModeConfig


@pytest.fixture(name="params")
def configured_params() -> Params:
    params: Params = {
        "expect_active": "ignore",
        "ieee_302_3ad_agg_id_missmatch_state": 1,
        "bonding_mode_states": {
            "mode_0": 0,
            "mode_1": 1,
            "mode_2": 2,
            "mode_3": 3,
            "mode_4": 0,
            "mode_5": 1,
            "mode_6": 2,
        },
    }
    return params


def data_for_test() -> Iterator[tuple[str, str]]:
    yield "mode_0", "round-robin"
    yield "mode_1", "active-backup"
    yield "mode_2", "xor"
    yield "mode_3", "broadcast"
    yield "mode_4", "802.3ad"
    yield "mode_5", "transmit"
    yield "mode_6", "adaptive"


@pytest.mark.parametrize("mode, mode_str", data_for_test())
def test_mode_matches_expected_state(mode: str, mode_str: str, params: Params) -> None:
    COPY_OF_DATA = DATA_FAILOVER[:]
    COPY_OF_DATA[2] = ["Bonding Mode", f"({mode_str})"]
    section: bonding.Section = lnx_bonding.parse_lnx_bonding(COPY_OF_DATA)
    check_result = list(check_bonding(item="bond0", params=params, section=section))
    expected_state = params["bonding_mode_states"][mode]  # type: ignore[literal-required]

    summary = f"Mode: {mode_str}"
    if State(expected_state) != State.OK:
        summary += " (not allowed)"

    assert check_result[1] == Result(state=State(expected_state), summary=summary)


def test_bonding_mode_states_not_configured(params: Params) -> None:
    section: bonding.Section = lnx_bonding.parse_lnx_bonding(DATA_FAILOVER)
    check_result = list(
        check_bonding(
            item="bond0",
            params={k: v for k, v in params.items() if k != "bonding_mode_states"},
            section=section,
        )
    )
    assert check_result[1] == Result(
        state=State(0), summary="Mode: fault-tolerance (active-backup)"
    )
