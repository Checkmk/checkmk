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
            {"disk": {"CPUCreditUsage": 99, "CPUCreditBalance": 2}},
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
def test_aws_rds_cpu_credits_discovery(
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_cpu_credits")]
    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_rds_cpu_credits_item_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_cpu_credits")]
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


def test_check_aws_rds_cpu_credits_metric_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_cpu_credits")]
    with pytest.raises(KeyError):
        list(
            check.check_function(
                item="disk",
                params={},
                section={"disk": {"CPUUtilization": 1}},
            )
        )


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"disk": {"CPUCreditUsage": 99, "CPUCreditBalance": 30, "BurstBalance": 30}},
            {"balance_levels_lower": (10, 5), "burst_balance_levels_lower": (10, 5)},
            [
                Result(state=State.OK, summary="CPU Credit Usage: 99.00"),
                Result(state=State.OK, summary="CPU Credit Balance: 30.00"),
                Metric("aws_cpu_credit_balance", 30.0),
                Result(state=State.OK, summary="Burst Balance: 30.00%"),
                Metric("aws_burst_balance", 30.0),
            ],
            id="If the levels are above the warn/crit levels, the check state will be OK with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"CPUCreditUsage": 99, "CPUCreditBalance": 8, "BurstBalance": 8}},
            {"balance_levels_lower": (10, 5), "burst_balance_levels_lower": (10, 5)},
            [
                Result(state=State.OK, summary="CPU Credit Usage: 99.00"),
                Result(
                    state=State.WARN,
                    summary="CPU Credit Balance: 8.00 (warn/crit below 10.00/5.00)",
                ),
                Metric("aws_cpu_credit_balance", 8.0),
                Result(
                    state=State.WARN, summary="Burst Balance: 8.00% (warn/crit below 10.00%/5.00%)"
                ),
                Metric("aws_burst_balance", 8.0),
            ],
            id="If the levels are below the warn levels, the check state will be WARN with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"CPUCreditUsage": 99, "CPUCreditBalance": 3, "BurstBalance": 3}},
            {"balance_levels_lower": (10, 5), "burst_balance_levels_lower": (10, 5)},
            [
                Result(state=State.OK, summary="CPU Credit Usage: 99.00"),
                Result(
                    state=State.CRIT,
                    summary="CPU Credit Balance: 3.00 (warn/crit below 10.00/5.00)",
                ),
                Metric("aws_cpu_credit_balance", 3.0),
                Result(
                    state=State.CRIT, summary="Burst Balance: 3.00% (warn/crit below 10.00%/5.00%)"
                ),
                Metric("aws_burst_balance", 3.0),
            ],
            id="If the levels are below the warn levels, the check state will be WARN with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"CPUCreditUsage": 99, "CPUCreditBalance": 30}},
            {"balance_levels_lower": (10, 5), "burst_balance_levels_lower": (10, 5)},
            [
                Result(state=State.OK, summary="CPU Credit Usage: 99.00"),
                Result(
                    state=State.OK,
                    summary="CPU Credit Balance: 30.00",
                ),
                Metric("aws_cpu_credit_balance", 30.0),
            ],
            id="If the BurstBalance metric is not present, no results are shown for it.",
        ),
    ],
)
def test_check_aws_rds_cpu_credits(
    section: Mapping[str, Mapping[str, float]],
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_cpu_credits")]
    check_result = list(
        check.check_function(
            item="disk",
            params=params,
            section=section,
        )
    )
    assert check_result[0] == Result(
        state=State.OK, summary="CPU Credit Usage: 99.00"
    )  # The first result is always OK and show the information about the CPU Credits Usage
    assert check_result == expected_check_result
