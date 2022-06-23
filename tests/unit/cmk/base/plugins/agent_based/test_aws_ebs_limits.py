#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.aws_ebs_limits import parse_aws_ebs_limits

_AWS_REGION = "eu-central-1"
_DEFAULT_PARAMS = {
    "block_store_snapshots": (None, 80.0, 90.0),
    "block_store_space_standard": (None, 80.0, 90.0),
    "block_store_space_io1": (None, 80.0, 90.0),
    "block_store_iops_io1": (None, 80.0, 90.0),
    "block_store_space_io2": (None, 80.0, 90.0),
    "block_store_iops_io2": (None, 80.0, 90.0),
    "block_store_space_gp2": (None, 80.0, 90.0),
    "block_store_space_gp3": (None, 80.0, 90.0),
    "block_store_space_sc1": (None, 80.0, 90.0),
    "block_store_space_st1": (None, 80.0, 90.0),
}
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


@pytest.fixture(name="ebs_limits_check")
def fixture_ebs_limits_check(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("aws_ebs_limits")]


def test_discover_ebs_limits(ebs_limits_check: CheckPlugin) -> None:
    parsed_section = parse_aws_ebs_limits(_STRING_TABLE)
    assert list(ebs_limits_check.discovery_function(parsed_section)) == [Service(item=_AWS_REGION)]


def test_check_ebs_limits(ebs_limits_check: CheckPlugin) -> None:
    parsed_section = parse_aws_ebs_limits(_STRING_TABLE)
    assert list(
        ebs_limits_check.check_function(
            item=_AWS_REGION, params=_DEFAULT_PARAMS, section=parsed_section
        )
    ) == [
        Result(state=State.OK, summary="No levels reached"),
        Metric("aws_ebs_block_store_snapshots", 56.0),
        Metric("aws_ebs_block_store_space_standard", 296352743424.0),
        Metric("aws_ebs_block_store_space_io1", 0.0),
        Metric("aws_ebs_block_store_iops_io1", 0.0),
        Metric("aws_ebs_block_store_space_io2", 0.0),
        Metric("aws_ebs_block_store_iops_io2", 0.0),
        Metric("aws_ebs_block_store_space_gp2", 1801738780672.0),
        Metric("aws_ebs_block_store_space_gp3", 0.0),
        Metric("aws_ebs_block_store_space_sc1", 0.0),
        Metric("aws_ebs_block_store_space_st1", 0.0),
        Result(
            state=State.OK,
            summary="10 additional details available",
            details="Block store snapshots: 56 (of max. 100000)\nCold HDD space: 0 B (of max. 300 TiB)\nGeneral Purpose SSD (gp2) space: 1.64 TiB (of max. 300 TiB)\nGeneral Purpose SSD (gp3) space: 0 B (of max. 300 TiB)\nMagnetic volumes space: 276 GiB (of max. 300 TiB)\nProvisioned IOPS SSD (io1) IO operations per second: 0/s (of max. 300000/s)\nProvisioned IOPS SSD (io1) space: 0 B (of max. 300 TiB)\nProvisioned IOPS SSD (io2) IO operations per second: 0/s (of max. 100000/s)\nProvisioned IOPS SSD (io2) space: 0 B (of max. 20.0 TiB)\nThroughput Optimized HDD space: 0 B (of max. 300 TiB)",
        ),
    ]
