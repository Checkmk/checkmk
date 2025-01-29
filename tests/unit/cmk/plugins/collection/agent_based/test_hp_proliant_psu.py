#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import hp_proliant_psu

STING_TABLE = [["0", "1", "3", "2", "80", "460"], ["0", "2", "3", "2", "450", "460"]]
PARAMS = hp_proliant_psu.Params(levels=(80.0, 90.0))


@pytest.fixture(name="section")
def fixure_section() -> hp_proliant_psu.Section:
    return hp_proliant_psu.parse_hp_proliant_psu(string_table=STING_TABLE)


def test_discovery(section: hp_proliant_psu.Section) -> None:
    services = list(hp_proliant_psu.discover_hp_proliant_psu(section))
    assert services == [Service(item="0/1"), Service(item="0/2"), Service(item="Total")]


def test_check_psu(section: hp_proliant_psu.Section) -> None:
    results = list(hp_proliant_psu.check_hp_proliant_psu("0/1", PARAMS, section))
    assert results == [
        Result(state=State.OK, summary="Chassis 0/Bay 1"),
        Result(state=State.OK, summary='State: "ok"'),
        Result(state=State.OK, summary="Usage: 80/460 Watts"),
        Metric("power_usage", 80.0),
        Result(state=State.OK, summary="Percentage: 17.39%"),
        Metric("power_usage_percentage", 17.391304347826086, levels=(80.0, 90.0)),
    ]


def test_check_psu_crit(section: hp_proliant_psu.Section) -> None:
    results = list(hp_proliant_psu.check_hp_proliant_psu("0/2", PARAMS, section))
    assert results == [
        Result(state=State.OK, summary="Chassis 0/Bay 2"),
        Result(state=State.OK, summary='State: "ok"'),
        Result(state=State.OK, summary="Usage: 450/460 Watts"),
        Metric("power_usage", 450.0),
        Result(state=State.CRIT, summary="Percentage: 97.83% (warn/crit at 80.00%/90.00%)"),
        Metric("power_usage_percentage", 97.82608695652173, levels=(80.0, 90.0)),
    ]


def test_check_psu_total(section: hp_proliant_psu.Section) -> None:
    results = list(hp_proliant_psu.check_hp_proliant_psu("Total", PARAMS, section))
    assert results == [
        Result(state=State.OK, summary="Usage: 530/920 Watts"),
        Metric("power_usage", 530.0),
        Result(state=State.OK, summary="Percentage: 57.61%"),
        Metric("power_usage_percentage", 57.608695652173914, levels=(80.0, 90.0)),
    ]
