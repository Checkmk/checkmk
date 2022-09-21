#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.check_api import MKCounterWrapped
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

METRICS = {
    "CPUCreditUsage": 0.5,
    "CPUCreditBalance": 75.0,
}


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            METRICS,
            [Service()],
            id="For every disk in the section a Service with no item is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_ec2_cpu_credits_discovery(
    section: Mapping[str, float],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2_cpu_credits")]
    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_ec2_cpu_credits_raises_error(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2_cpu_credits")]
    with pytest.raises(MKCounterWrapped):
        list(
            check.check_function(
                item="",
                params={"balance_levels_lower": (10, 5)},
                section={},
            )
        )


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            {
                "CPUCreditUsage": 0.5,
                "CPUCreditBalance": 75.0,
            },
            [
                Result(state=State.OK, summary="Usage: 0.50"),
                Result(state=State.OK, summary="Balance: 75.00"),
                Metric("aws_cpu_credit_balance", 75.0),
            ],
            id="If the CPUCreditBalance is above the warn/crit levels the check state is OK.",
        ),
        pytest.param(
            {
                "CPUCreditUsage": 0.5,
                "CPUCreditBalance": 8.0,
            },
            [
                Result(state=State.OK, summary="Usage: 0.50"),
                Result(state=State.WARN, summary="Balance: 8.00 (warn/crit below 10.00/5.00)"),
                Metric("aws_cpu_credit_balance", 8.0),
            ],
            id="If the CPUCreditBalance is below the warn level the check state is WARN.",
        ),
        pytest.param(
            {
                "CPUCreditUsage": 0.5,
                "CPUCreditBalance": 4.0,
            },
            [
                Result(state=State.OK, summary="Usage: 0.50"),
                Result(state=State.CRIT, summary="Balance: 4.00 (warn/crit below 10.00/5.00)"),
                Metric("aws_cpu_credit_balance", 4.0),
            ],
            id="If the CPUCreditBalance is below the crit level the check state is CRIT.",
        ),
    ],
)
def test_check_aws_ec2_cpu_credits(
    section: Mapping[str, float],
    expected_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2_cpu_credits")]
    check_result = list(
        check.check_function(
            item="",
            params={"balance_levels_lower": (10, 5)},
            section=section,
        )
    )
    assert check_result == expected_result
