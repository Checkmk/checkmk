#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.aws.agent_based.aws_ebs_limits import (
    AWS_EBS_LIMITS_DEFAULT_PARAMS,
    check_aws_ebs_limits,
    discover_aws_ebs_limits,
    parse_aws_ebs_limits,
)

_AWS_REGION = "eu-central-1"
_STRING_TABLE = [
    [
        '[["block_store_snapshots",',
        '"Block',
        "store",
        'snapshots",',
        "100000,",
        "56,",
        '"eu-central-1"],',
        '["block_store_space_standard",',
        '"Magnetic',
        "volumes",
        'space",',
        "300,",
        "276,",
        '"eu-central-1"],',
        '["block_store_space_io1",',
        '"Provisioned',
        "IOPS",
        "SSD",
        "(io1)",
        'space",',
        "300,",
        "0,",
        '"eu-central-1"],',
        '["block_store_iops_io1",',
        '"Provisioned',
        "IOPS",
        "SSD",
        "(io1)",
        "IO",
        "operations",
        "per",
        'second",',
        "300000,",
        "0,",
        '"eu-central-1"],',
        '["block_store_space_io2",',
        '"Provisioned',
        "IOPS",
        "SSD",
        "(io2)",
        'space",',
        "20,",
        "0,",
        '"eu-central-1"],',
        '["block_store_iops_io2",',
        '"Provisioned',
        "IOPS",
        "SSD",
        "(io2)",
        "IO",
        "operations",
        "per",
        'second",',
        "100000,",
        "0,",
        '"eu-central-1"],',
        '["block_store_space_gp2",',
        '"General',
        "Purpose",
        "SSD",
        "(gp2)",
        'space",',
        "300,",
        "1678,",
        '"eu-central-1"],',
        '["block_store_space_gp3",',
        '"General',
        "Purpose",
        "SSD",
        "(gp3)",
        'space",',
        "300,",
        "0,",
        '"eu-central-1"],',
        '["block_store_space_sc1",',
        '"Cold',
        "HDD",
        'space",',
        "300,",
        "0,",
        '"eu-central-1"],',
        '["block_store_space_st1",',
        '"Throughput',
        "Optimized",
        "HDD",
        'space",',
        "300,",
        "0,",
        '"eu-central-1"]]',
    ]
]


def test_discover_ebs_limits() -> None:
    parsed_section = parse_aws_ebs_limits(_STRING_TABLE)
    assert list(discover_aws_ebs_limits(parsed_section)) == [Service(item=_AWS_REGION)]


def test_check_ebs_limits() -> None:
    parsed_section = parse_aws_ebs_limits(_STRING_TABLE)
    assert list(
        check_aws_ebs_limits(
            item=_AWS_REGION, params=AWS_EBS_LIMITS_DEFAULT_PARAMS, section=parsed_section
        )
    ) == [
        Metric("aws_ebs_block_store_snapshots", 56.0),
        Result(state=State.OK, notice="Block store snapshots: 56 (of max. 100000), 0.06%"),
        Metric("aws_ebs_block_store_space_standard", 296352743424.0),
        Result(state=State.OK, notice="Magnetic volumes space: 276 GiB (of max. 300 TiB), 0.09%"),
        Metric("aws_ebs_block_store_space_io1", 0.0),
        Result(
            state=State.OK, notice="Provisioned IOPS SSD (io1) space: 0 B (of max. 300 TiB), 0%"
        ),
        Metric("aws_ebs_block_store_iops_io1", 0.0),
        Result(
            state=State.OK,
            notice="Provisioned IOPS SSD (io1) IO operations per second: 0/s (of max. 300000/s), 0%",
        ),
        Metric("aws_ebs_block_store_space_io2", 0.0),
        Result(
            state=State.OK, notice="Provisioned IOPS SSD (io2) space: 0 B (of max. 20.0 TiB), 0%"
        ),
        Metric("aws_ebs_block_store_iops_io2", 0.0),
        Result(
            state=State.OK,
            notice="Provisioned IOPS SSD (io2) IO operations per second: 0/s (of max. 100000/s), 0%",
        ),
        Metric("aws_ebs_block_store_space_gp2", 1801738780672.0),
        Result(
            state=State.OK,
            notice="General Purpose SSD (gp2) space: 1.64 TiB (of max. 300 TiB), 0.55%",
        ),
        Metric("aws_ebs_block_store_space_gp3", 0.0),
        Result(state=State.OK, notice="General Purpose SSD (gp3) space: 0 B (of max. 300 TiB), 0%"),
        Metric("aws_ebs_block_store_space_sc1", 0.0),
        Result(state=State.OK, notice="Cold HDD space: 0 B (of max. 300 TiB), 0%"),
        Metric("aws_ebs_block_store_space_st1", 0.0),
        Result(state=State.OK, notice="Throughput Optimized HDD space: 0 B (of max. 300 TiB), 0%"),
    ]
