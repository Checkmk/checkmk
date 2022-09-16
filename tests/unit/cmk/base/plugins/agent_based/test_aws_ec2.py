#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.aws_ec2 import (
    check_aws_ec2_disk_io,
    check_aws_ec2_network_io,
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


def test_check_aws_ec2_network_io() -> None:
    assert list(check_aws_ec2_network_io("Summary", {}, {"NetworkIn": 1, "NetworkOut": 2,},)) == [
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
def test_aws_ebs_discovery(
    section: Section,
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_aws_ec2_disk_io(section)) == discovery_result


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
