#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, inventory_result",
    [
        pytest.param(
            [
                ["1996492800", "1", "49"],
                ["1996492801", "4", "-1"],
                ["1996492802", "4", "-1"],
            ],
            [Service(item="1996492800")],
            id="If the status of the PFM is not 4, the PFM is discovered.",
        ),
        pytest.param(
            [
                ["1996492801", "4", "-1"],
                ["1996492802", "4", "-1"],
            ],
            [],
            id="If the status of the PFM is 4, no service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If the info is empty, no service is discovered.",
        ),
    ],
)
def test_inventory_fjdarye500_pfm(
    info: StringTable,
    inventory_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("fjdarye500_pfm")]
    assert list(check.discovery_function(info)) == inventory_result


@pytest.mark.parametrize(
    "item, params, info, check_result",
    [
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            [
                ["1996492800", "1", "49"],
            ],
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 1 or 5, the result of the first check result is OK with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            [
                ["1996492800", "2", "49"],
            ],
            [
                Result(state=State.CRIT, summary="Status: alarm"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 2 or 4, the result of the first check result is CRIT with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            [
                ["1996492800", "3", "49"],
            ],
            [
                Result(state=State.WARN, summary="Status: warning"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 3, the result of the first check result is WARN with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            [
                ["1996492800", "6", "49"],
            ],
            [
                Result(state=State.UNKNOWN, summary="Status: undefined"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 6, the result of the first check result is UNKNOWN with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            [
                ["1996492800", "1", "19"],
            ],
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(
                    state=State.WARN,
                    summary="Health lifetime: 19.00% (warn/crit below 20.00%/15.00%)",
                ),
            ],
            id="If the health lifetime of the PFM is below the WARN level, the result of the second check result is WARN with a description of the thresholds.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            [
                ["1996492800", "1", "13"],
            ],
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(
                    state=State.CRIT,
                    summary="Health lifetime: 13.00% (warn/crit below 20.00%/15.00%)",
                ),
            ],
            id="If the health lifetime of the PFM is below the CRIT level, the result of the second check result is CRIT with a description of the thresholds.",
        ),
    ],
)
def test_check_fjdarye500_pfm(
    item: str,
    params: Mapping[str, tuple[float, float]],
    info: StringTable,
    check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("fjdarye500_pfm")]
    assert (
        list(
            check.check_function(
                item=item,
                params=params,
                section=info,
            )
        )
        == check_result
    )
