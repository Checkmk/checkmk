#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.aws.agent_based.aws_ec2 import (
    check_aws_ec2_cpu_credits,
    check_aws_ec2_cpu_util,
    check_aws_ec2_disk_io,
    check_aws_ec2_network_io,
    check_aws_ec2_status_check,
    discover_aws_ec2,
    discover_aws_ec2_cpu_credits,
    discover_aws_ec2_cpu_util,
    discover_aws_ec2_disk_io,
    Section,
)

METRICS = {
    "CPUCreditUsage": 0.267425,
    "CPUCreditBalance": 75.962754,
    "CPUUtilization": 2.7081828285634897,
    "DiskReadOps": 0.0,
    "DiskWriteOps": 0.0,
    "DiskReadBytes": 0.0,
    "DiskWriteBytes": 0.0,
    "NetworkIn": 42.0,
    "NetworkOut": 28.0,
    "StatusCheckFailed_Instance": 0.0,
    "StatusCheckFailed_System": 0.0,
}


@pytest.mark.usefixtures("initialised_item_state")
def test_check_aws_ec2_network_io() -> None:
    assert list(
        check_aws_ec2_network_io(
            "Summary",
            {},
            {
                "NetworkIn": 1,
                "NetworkOut": 2,
            },
        )
    ) == [
        Result(state=State.OK, summary="[0]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="Speed: unknown"),
        Result(state=State.OK, summary="In: 0.02 B/s"),
        Metric("in", 0.016666666666666666, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Out: 0.03 B/s"),
        Metric("out", 0.03333333333333333, boundaries=(0.0, None)),
    ]


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            METRICS,
            [Service(item="Summary")],
            id="For every disk in the section a Service is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_ec2_disk_io_discovery(
    section: Section,
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_aws_ec2_disk_io(section)) == discovery_result


@pytest.mark.usefixtures("initialised_item_state")
def test_check_aws_ec2_disk_io() -> None:
    check_result = list(check_aws_ec2_disk_io(item="Summary", params={}, section=METRICS))

    assert len(check_result) == 8
    assert check_result == [
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=State.OK, summary="Write: 0.00 B/s"),
        Metric("disk_write_throughput", 0.0),
        Result(state=State.OK, notice="Read operations: 0.00/s"),
        Metric("disk_read_ios", 0.0),
        Result(state=State.OK, notice="Write operations: 0.00/s"),
        Metric("disk_write_ios", 0.0),
    ]


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
def test_aws_ec2_discovery(
    section: Mapping[str, float],
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_aws_ec2(section)) == discovery_result


def test_check_aws_ec2_state_ok() -> None:
    check_result = list(
        check_aws_ec2_status_check(
            section=METRICS,
        )
    )
    assert check_result == [
        Result(state=State.OK, summary="System: Passed"),
        Result(state=State.OK, summary="Instance: Passed"),
    ]


def test_check_aws_ec2_state_crit() -> None:
    check_result = list(
        check_aws_ec2_status_check(
            section={
                "StatusCheckFailed_Instance": 1.0,
                "StatusCheckFailed_System": 2.0,
            },
        )
    )
    assert check_result == [
        Result(state=State.CRIT, summary="System: Failed"),
        Result(state=State.CRIT, summary="Instance: Failed"),
    ]


def test_check_aws_ec2_raise_error() -> None:
    # If both of the fields are missing, the check raises a MKCounterWrapped error

    with pytest.raises(IgnoreResultsError):
        list(
            check_aws_ec2_status_check(
                section={},
            )
        )


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {"CPUUtilization": 99},
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
def test_aws_ec2_cpu_util_discovery(
    section: Mapping[str, float],
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_aws_ec2_cpu_util(section)) == discovery_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"CPUUtilization": 99},
            {},
            [
                Result(state=State.OK, summary="Total CPU: 99.00%"),
                Metric("util", 99.0, boundaries=(0.0, None)),
            ],
            id="If the ruleset is initialized and left blank, the result always be OK and display the appropriate description.",
        ),
        pytest.param(
            {"CPUUtilization": 70},
            {"util": (90.0, 95.0)},
            [
                Result(state=State.OK, summary="Total CPU: 70.00%"),
                Metric("util", 70.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="If the CPU Utilization is below the set boundaries, the result is OK and the appropriate description is displayed.",
        ),
        pytest.param(
            {"CPUUtilization": 91},
            {"util": (90.0, 95.0)},
            [
                Result(state=State.WARN, summary="Total CPU: 91.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 91.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="If the CPU Utilization is above the set warning level, the result is WARN and the appropriate description is displayed.",
        ),
        pytest.param(
            {"CPUUtilization": 99},
            {"util": (90.0, 95.0)},
            [
                Result(state=State.CRIT, summary="Total CPU: 99.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 99.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="If the CPU Utilization is above the set critical level, the result is CRIT and the appropriate description is displayed.",
        ),
    ],
)
def test_check_aws_ec2_cpu_util(
    section: Mapping[str, float],
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    check_result = list(
        check_aws_ec2_cpu_util(
            params=params,
            section=section,
        )
    )
    assert check_result == expected_check_result


def test_check_aws_ec2_cpu_util_no_data_raises_error() -> None:
    # If the CPUUtilization field are missing, the check raises a MKCounterWrapped error
    with pytest.raises(IgnoreResultsError):
        list(
            check_aws_ec2_cpu_util(
                params={},
                section={},
            )
        )


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
    section: Section,
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_aws_ec2_cpu_credits(section)) == discovery_result


def test_check_aws_ec2_cpu_credits_raises_error() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            check_aws_ec2_cpu_credits(
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
    section: Section,
    expected_result: Sequence[Result | Metric],
) -> None:
    check_result = list(
        check_aws_ec2_cpu_credits(
            params={"balance_levels_lower": (10, 5)},
            section=section,
        )
    )
    assert check_result == expected_result
