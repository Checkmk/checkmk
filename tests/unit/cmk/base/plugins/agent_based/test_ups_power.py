#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.snmp import get_parsed_snmp_section, snmp_is_detected

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

# walks/usv-liebert
DATA0 = """
.1.3.6.1.2.1.1.2.0  .1.3.6.1.4.1.476.1.42
.1.3.6.1.2.1.33.1.4.4.1.2.1  230
.1.3.6.1.2.1.33.1.4.4.1.2.2  230
.1.3.6.1.2.1.33.1.4.4.1.2.3  229
.1.3.6.1.2.1.33.1.4.4.1.4.1  2300
.1.3.6.1.2.1.33.1.4.4.1.4.2  3500
.1.3.6.1.2.1.33.1.4.4.1.4.3  4800
"""


@pytest.mark.usefixtures("fix_register")
def test_ups_power_detect() -> None:
    assert snmp_is_detected(SectionName("ups_power"), DATA0)


def test_ups_power_discover(fix_register: FixRegister) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("epower")]
    parsed = get_parsed_snmp_section(SectionName("ups_power"), DATA0)

    assert list(plugin.discovery_function(parsed)) == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
    ]


@pytest.mark.parametrize(
    "params, result",
    [
        (
            {"levels_lower": (20, 1)},
            [
                Result(state=State.OK, summary="Power: 3500 W"),
                Metric("power", 3500.0),
            ],
        ),
        (
            {"levels_lower": (4000, 3000)},
            [
                Result(state=State.WARN, summary="Power: 3500 W (warn/crit below 4000 W/3000 W)"),
                Metric("power", 3500.0),
            ],
        ),
        (
            {"levels_lower": (6000, 4000)},
            [
                Result(state=State.CRIT, summary="Power: 3500 W (warn/crit below 6000 W/4000 W)"),
                Metric("power", 3500.0),
            ],
        ),
    ],
)
def test_ups_power_check(fix_register: FixRegister, params: dict, result: CheckResult) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("epower")]
    parsed = get_parsed_snmp_section(SectionName("ups_power"), DATA0)

    assert list(plugin.check_function(item="2", params=params, section=parsed)) == result
