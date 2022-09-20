#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {"disk": {"CPUUtilization": 99}},
            [Service(item="disk")],
            id="For every disk in the section a Service with no item is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_rds_discovery(
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds")]
    assert list(check.discovery_function(section)) == discovery_result


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"disk": {"CPUUtilization": 99}},
            {},
            [
                Result(state=State.OK, summary="Total CPU: 99.00%"),
                Metric("util", 99.0, boundaries=(0.0, 100.0)),
            ],
            id="If the ruleset is initialized and left blank, the result always be OK and display the appropriate description.",
        ),
        pytest.param(
            {"disk": {"CPUUtilization": 70}},
            {"util": (90.0, 95.0)},
            [
                Result(state=State.OK, summary="Total CPU: 70.00%"),
                Metric("util", 70.0, levels=(90.0, 95.0), boundaries=(0.0, 100.0)),
            ],
            id="If the CPU Utilization is below the set boundaries, the result is OK and the appropriate description is displayed.",
        ),
        pytest.param(
            {"disk": {"CPUUtilization": 91}},
            {"util": (90.0, 95.0)},
            [
                Result(state=State.WARN, summary="Total CPU: 91.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 91.0, levels=(90.0, 95.0), boundaries=(0.0, 100.0)),
            ],
            id="If the CPU Utilization is above the set warning level, the result is WARN and the appropriate description is displayed.",
        ),
        pytest.param(
            {"disk": {"CPUUtilization": 99}},
            {"util": (90.0, 95.0)},
            [
                Result(state=State.CRIT, summary="Total CPU: 99.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 99.0, levels=(90.0, 95.0), boundaries=(0.0, 100.0)),
            ],
            id="If the CPU Utilization is above the set critical level, the result is CRIT and the appropriate description is displayed.",
        ),
    ],
)
def test_check_aws_rds(
    section: Mapping[str, Mapping[str, float]],
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds")]
    check_result = list(
        check.check_function(
            item="disk",
            params=params,
            section=section,
        )
    )
    assert check_result == expected_check_result


def test_check_aws_rds_item_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds")]
    assert (
        list(
            check.check_function(
                item="disk",
                params={},
                section={},
            )
        )
        == []
    )
