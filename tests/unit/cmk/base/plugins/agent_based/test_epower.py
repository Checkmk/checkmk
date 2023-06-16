#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from tests.testlib.snmp import get_parsed_snmp_section

from cmk.utils.sectionname import SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.epower import check_epower, discover_epower

# SUP-12323
APC_SYMMETRA_0 = """
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.1 1
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.2 2
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.2.1.3 3
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.1 1309
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.2 1344
.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7.1.3 1783
"""

# walks/usv-apc-symmetra-new
APC_SYMMETRA_1 = """
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

# walks/usv-liebert
UPS_POWER_0 = """
.1.3.6.1.2.1.33.1.4.4.1.2.1  230
.1.3.6.1.2.1.33.1.4.4.1.2.2  230
.1.3.6.1.2.1.33.1.4.4.1.2.3  229
.1.3.6.1.2.1.33.1.4.4.1.4.1  2300
.1.3.6.1.2.1.33.1.4.4.1.4.2  3500
.1.3.6.1.2.1.33.1.4.4.1.4.3  4800
"""


@pytest.mark.parametrize(
    "walk, section_name, result",
    [
        pytest.param(
            APC_SYMMETRA_0,
            SectionName("apc_symmetra_power"),
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="apc-symmetra-0",
        ),
        pytest.param(
            APC_SYMMETRA_1,
            SectionName("apc_symmetra_power"),
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="apc-symmetra-1",
        ),
        pytest.param(
            UPS_POWER_0,
            SectionName("ups_power"),
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="ups-power-0",
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_power_discover(
    walk: str,
    section_name: SectionName,
    result: DiscoveryResult,
    as_path: Callable[[str], Path],
) -> None:
    parsed = cast(dict[str, int], get_parsed_snmp_section(section_name, as_path(walk)))

    assert list(discover_epower(parsed)) == result


@pytest.mark.parametrize(
    "walk, section_name, item, params, result",
    [
        pytest.param(
            APC_SYMMETRA_0,
            SectionName("apc_symmetra_power"),
            "1",
            {"levels_lower": (20, 1)},
            [
                Result(state=State.OK, summary="Power: 1309 W"),
                Metric("power", 1309.0),
            ],
            id="apc-symmetra-0",
        ),
        pytest.param(
            APC_SYMMETRA_1,
            SectionName("apc_symmetra_power"),
            "2",
            {"levels_lower": (20, 1)},
            [
                Result(state=State.OK, summary="Power: 2000 W"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1",
        ),
        pytest.param(
            APC_SYMMETRA_1,
            SectionName("apc_symmetra_power"),
            "2",
            {"levels_lower": (3000, 2000)},
            [
                Result(state=State.WARN, summary="Power: 2000 W (warn/crit below 3000 W/2000 W)"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1-warn",
        ),
        pytest.param(
            APC_SYMMETRA_1,
            SectionName("apc_symmetra_power"),
            "2",
            {"levels_lower": (6000, 3000)},
            [
                Result(state=State.CRIT, summary="Power: 2000 W (warn/crit below 6000 W/3000 W)"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1-crit",
        ),
        pytest.param(
            UPS_POWER_0,
            SectionName("ups_power"),
            "2",
            {"levels_lower": (20, 1)},
            [
                Result(state=State.OK, summary="Power: 3500 W"),
                Metric("power", 3500.0),
            ],
            id="ups-power-2-ok",
        ),
        pytest.param(
            UPS_POWER_0,
            SectionName("ups_power"),
            "2",
            {"levels_lower": (4000, 3000)},
            [
                Result(state=State.WARN, summary="Power: 3500 W (warn/crit below 4000 W/3000 W)"),
                Metric("power", 3500.0),
            ],
            id="ups-power-2-warn",
        ),
        pytest.param(
            UPS_POWER_0,
            SectionName("ups_power"),
            "2",
            {"levels_lower": (6000, 4000)},
            [
                Result(state=State.CRIT, summary="Power: 3500 W (warn/crit below 6000 W/4000 W)"),
                Metric("power", 3500.0),
            ],
            id="ups-power-2-crit",
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_epower_check(
    walk: str,
    section_name: SectionName,
    item: str,
    params: Any,
    result: CheckResult,
    as_path: Callable[[str], Path],
) -> None:
    parsed = cast(dict[str, int], get_parsed_snmp_section(section_name, as_path(walk)))

    assert list(check_epower(item=item, params=params, section=parsed)) == result
