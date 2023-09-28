#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import hp_proliant_psu
from cmk.base.plugins.agent_based.agent_based_api import v1

STING_TABLE = [["0", "1", "3", "2", "80", "460"], ["0", "2", "3", "2", "450", "460"]]
PARAMS = hp_proliant_psu.Params(levels=(80.0, 90.0))


@pytest.fixture(name="section")
def fixure_section() -> hp_proliant_psu.Section:
    return hp_proliant_psu.parse_hp_proliant_psu(string_table=STING_TABLE)


def test_discovery(section: hp_proliant_psu.Section) -> None:
    services = list(hp_proliant_psu.discover_hp_proliant_psu(section))
    assert services == [v1.Service(item="0/1"), v1.Service(item="0/2"), v1.Service(item="Total")]


def test_check_psu(section: hp_proliant_psu.Section) -> None:
    results = list(hp_proliant_psu.check_hp_proliant_psu("0/1", PARAMS, section))
    assert results == [
        v1.Result(state=v1.State.OK, summary="Chassis 0/Bay 1"),
        v1.Result(state=v1.State.OK, summary='State: "ok"'),
        v1.Result(state=v1.State.OK, summary="Usage: 80/460 Watts"),
        v1.Metric("power_usage", 80.0),
        v1.Result(state=v1.State.OK, summary="Percentage: 17.39%"),
        v1.Metric("power_usage_percentage", 17.391304347826086, levels=(80.0, 90.0)),
    ]


def test_check_psu_crit(section: hp_proliant_psu.Section) -> None:
    results = list(hp_proliant_psu.check_hp_proliant_psu("0/2", PARAMS, section))
    assert results == [
        v1.Result(state=v1.State.OK, summary="Chassis 0/Bay 2"),
        v1.Result(state=v1.State.OK, summary='State: "ok"'),
        v1.Result(state=v1.State.OK, summary="Usage: 450/460 Watts"),
        v1.Metric("power_usage", 450.0),
        v1.Result(state=v1.State.CRIT, summary="Percentage: 97.83% (warn/crit at 80.00%/90.00%)"),
        v1.Metric("power_usage_percentage", 97.82608695652173, levels=(80.0, 90.0)),
    ]


def test_check_psu_total(section: hp_proliant_psu.Section) -> None:
    results = list(hp_proliant_psu.check_hp_proliant_psu("Total", PARAMS, section))
    assert results == [
        v1.Result(state=v1.State.OK, summary="Usage: 530/920 Watts"),
        v1.Metric("power_usage", 530.0),
        v1.Result(state=v1.State.OK, summary="Percentage: 57.61%"),
        v1.Metric("power_usage_percentage", 57.608695652173914, levels=(80.0, 90.0)),
    ]
