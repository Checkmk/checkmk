#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from tests.testlib.snmp import get_parsed_snmp_section, snmp_is_detected

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

# SUP-12323
DATA0 = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.318.1.3.2.12
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1 1
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.2 2
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.3 3
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1 1309
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.2 1344
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.3 1783
"""

# walks/usv-apc-symmetra-new
DATA1 = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.318.1.3.28.33
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1.1 1
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1.2 2
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1.3 3
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1.4 12
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1.5 23
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1.6 31
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1.1 4000
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1.2 2000
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1.3 3000
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1.4 -1
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1.5 -1
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1.6 -1
"""


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "walk",
    [
        pytest.param(DATA0, id="data0"),
        pytest.param(DATA1, id="data1"),
    ],
)
def test_apc_symmetra_power_detect(walk: str) -> None:
    assert snmp_is_detected(SectionName("apc_symmetra_power"), walk)


@pytest.mark.parametrize(
    "walk, result",
    [
        pytest.param(
            DATA0,
            [
                Service(item="1", parameters={"auto-migration-wrapper-key": (20, 1)}),
                # XXX: this is wrong, and should include the other two phases
            ],
            id="data0",
        ),
        pytest.param(
            DATA1,
            [
                Service(item="1", parameters={"auto-migration-wrapper-key": (20, 1)}),
                Service(item="2", parameters={"auto-migration-wrapper-key": (20, 1)}),
                Service(item="3", parameters={"auto-migration-wrapper-key": (20, 1)}),
            ],
            id="data1",
        ),
    ],
)
def test_apc_symmetra_power_discover(
    fix_register: FixRegister, walk: str, result: DiscoveryResult
) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("apc_symmetra_power")]

    parsed = get_parsed_snmp_section(SectionName("apc_symmetra_power"), walk)

    assert list(plugin.discovery_function(parsed)) == result


@pytest.mark.parametrize(
    "walk, item, params, result",
    [
        pytest.param(
            DATA0,
            "1",
            {"auto-migration-wrapper-key": (20, 1)},
            [
                Result(
                    state=State.OK, summary="current power: 1309 W, warn/crit at and below 20/1 W"
                ),
                Metric("power", 1309.0, levels=(20.0, 1.0), boundaries=(0.0, None)),
            ],
            id="data0",
        ),
        pytest.param(
            DATA1,
            "2",
            {"auto-migration-wrapper-key": (20, 1)},
            [
                Result(
                    state=State.OK, summary="current power: 2000 W, warn/crit at and below 20/1 W"
                ),
                Metric("power", 2000.0, levels=(20.0, 1.0), boundaries=(0.0, None)),
            ],
            id="data1",
        ),
        pytest.param(
            DATA1,
            "2",
            {"auto-migration-wrapper-key": (3000, 2000)},
            [
                Result(
                    state=State.WARN,
                    summary="current power: 2000 W, warn/crit at and below 3000/2000 W",
                ),
                Metric("power", 2000.0, levels=(3000.0, 2000.0), boundaries=(0.0, None)),
            ],
            id="data1-warn",
        ),
        pytest.param(
            DATA1,
            "2",
            {"auto-migration-wrapper-key": (6000, 3000)},
            [
                Result(
                    state=State.CRIT,
                    summary="current power: 2000 W, warn/crit at and below 6000/3000 W",
                ),
                Metric("power", 2000.0, levels=(6000.0, 3000.0), boundaries=(0.0, None)),
            ],
            id="data1-crit",
        ),
    ],
)
def test_apc_symmetra_power_check(
    fix_register: FixRegister, walk: str, item: str, params: Any, result: CheckResult
) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("apc_symmetra_power")]

    parsed = get_parsed_snmp_section(SectionName("apc_symmetra_power"), walk)

    assert list(plugin.check_function(item=item, params=params, section=parsed)) == result
