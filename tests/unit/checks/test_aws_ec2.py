#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

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
    section: Mapping[str, float],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2_disk_io")]

    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_ec2_disk_io(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2_disk_io")]
    check_result = list(check.check_function(item="Summary", params={}, section=METRICS))
    assert len((check_result)) == 8
    assert check_result == [
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=State.OK, summary="Write: 0.00 B/s"),
        Metric("disk_write_throughput", 0.0),
        Result(state=State.OK, summary="Read operations: 0.00 1/s"),
        Metric("disk_read_ios", 0.0),
        Result(state=State.OK, summary="Write operations: 0.00 1/s"),
        Metric("disk_write_ios", 0.0),
    ]
