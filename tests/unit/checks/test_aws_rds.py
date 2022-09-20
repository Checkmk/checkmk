#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

SECTION = {
    "database-1 [eu-central-1]": {
        "BinLogDiskUsage": 1783.4,
        "DBInstanceIdentifier": "database-1",
        "AllocatedStorage": 21480000000.0,
        "Region": "eu-central-1",
        "BurstBalance": 100.0,
        "CPUUtilization": 2.3550349634157652,
        "CPUCreditUsage": 0.116523,
        "CPUCreditBalance": 0.403469,
        "DatabaseConnections": 0.0,
        "DiskQueueDepth": 0.0002666533349034978,
        "NetworkReceiveThroughput": 417.41570964272285,
        "NetworkTransmitThroughput": 2671.1907577121706,
        "ReadIOPS": 0.23333527781018573,
        "ReadLatency": 4e-05,
        "ReadThroughput": 136.53447113007437,
        "WriteIOPS": 0.3249847523733059,
        "WriteLatency": 0.00024792140430921573,
        "WriteThroughput": 3338.060601250865,
    },
}


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            SECTION,
            [Service(item="database-1 [eu-central-1]")],
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
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_disk_io")]

    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_rds_disk_io(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_disk_io")]
    check_result = list(
        check.check_function(
            item="database-1 [eu-central-1]",
            params={},
            section=SECTION,
        )
    )
    assert len(check_result) == 12
    assert check_result == [
        Result(state=State.OK, summary="Read: 137 B/s"),
        Metric("disk_read_throughput", 136.53447113007437),
        Result(state=State.OK, summary="Write: 3.34 kB/s"),
        Metric("disk_write_throughput", 3338.060601250865),
        Result(state=State.OK, summary="Read latency: 40.00 ms"),
        Metric("disk_read_latency", 0.04),
        Result(state=State.OK, summary="Write latency: 247.92 ms"),
        Metric("disk_write_latency", 0.24792140430921572),
        Result(state=State.OK, summary="Read operations: 0.23 1/s"),
        Metric("disk_read_ios", 0.23333527781018573),
        Result(state=State.OK, summary="Write operations: 0.32 1/s"),
        Metric("disk_write_ios", 0.3249847523733059),
    ]


def test_check_aws_rds_disk_io_item_not_foung(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_disk_io")]
    check_result = list(
        check.check_function(
            item="item_not_found",
            params={},
            section=SECTION,
        )
    )
    assert check_result == []
