#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, cast

import pytest

from tests.testlib.snmp import get_parsed_snmp_section

from cmk.utils.type_defs import SectionName

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


@pytest.mark.parametrize(
    "walk, result",
    [
        pytest.param(
            APC_SYMMETRA_0,
            [
                Service(item="1"),
                # XXX: this is wrong, and should include the other two phases
            ],
            id="apc-symmetra-0",
        ),
        pytest.param(
            APC_SYMMETRA_1,
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="apc-symmetra-1",
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_power_discover(walk: str, result: DiscoveryResult) -> None:
    parsed = cast(dict[str, int], get_parsed_snmp_section(SectionName("apc_symmetra_power"), walk))

    assert list(discover_epower(parsed)) == result


@pytest.mark.parametrize(
    "walk, item, params, result",
    [
        pytest.param(
            APC_SYMMETRA_0,
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
            "2",
            {"levels_lower": (6000, 3000)},
            [
                Result(state=State.CRIT, summary="Power: 2000 W (warn/crit below 6000 W/3000 W)"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1-crit",
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_epower_check(walk: str, item: str, params: Any, result: CheckResult) -> None:
    parsed = cast(dict[str, int], get_parsed_snmp_section(SectionName("apc_symmetra_power"), walk))

    assert list(check_epower(item=item, params=params, section=parsed)) == result
