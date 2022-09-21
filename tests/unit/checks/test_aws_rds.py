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
            {"disk": {"ReplicationSlotDiskUsage": 60.0}},
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
def test_aws_rds_replication_slot_usage_discovery(
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replication_slot_usage")]
    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_rds_replication_slot_usage_item_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replication_slot_usage")]
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


def test_check_aws_rds_replication_slot_usage_metric_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replication_slot_usage")]
    with pytest.raises(KeyError):
        list(
            check.check_function(
                item="disk",
                params={},
                section={"disk": {"CPUUtilization": 1}},
            )
        )


def test_check_aws_rds_replication_slot_usage_no_allocated_storage(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replication_slot_usage")]
    check_result = list(
        check.check_function(
            item="disk",
            params={},
            section={"disk": {"ReplicationSlotDiskUsage": 60.0}},
        )
    )
    assert check_result == [
        Result(state=State.OK, summary="60 B"),
        Result(state=State.WARN, summary="Cannot calculate usage"),
    ]


def test_check_aws_rds_replication_slot_usage_allocated_storage_is_zero(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replication_slot_usage")]
    check_result = list(
        check.check_function(
            item="disk",
            params={},
            section={"disk": {"ReplicationSlotDiskUsage": 60.0, "AllocatedStorage": 0.0}},
        )
    )
    assert check_result == [
        Result(state=State.OK, summary="60 B"),
        Result(state=State.WARN, summary="Cannot calculate usage"),
    ]


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"disk": {"ReplicationSlotDiskUsage": 60.0, "AllocatedStorage": 4000.0}},
            {"levels": (90, 95)},
            [
                Result(state=State.OK, summary="60 B"),
                Result(state=State.OK, summary="1.50%"),
                Metric("aws_rds_replication_slot_disk_usage", 1.5, levels=(90.0, 95.0)),
            ],
            id="If the ReplicationSlotDiskUsage levels are below the warn/crit levels, the check state will be OK with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"ReplicationSlotDiskUsage": 60.0, "AllocatedStorage": 65.0}},
            {"levels": (90, 95)},
            [
                Result(state=State.OK, summary="60 B"),
                Result(state=State.WARN, summary="92.31% (warn/crit at 90.00%/95.00%)"),
                Metric(
                    "aws_rds_replication_slot_disk_usage", 92.3076923076923, levels=(90.0, 95.0)
                ),
            ],
            id="If the ReplicationSlotDiskUsage levels are above the warn levels, the check state will be WARN with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"ReplicationSlotDiskUsage": 60.0, "AllocatedStorage": 60.0}},
            {"levels": (90, 95)},
            [
                Result(state=State.OK, summary="60 B"),
                Result(state=State.CRIT, summary="100.00% (warn/crit at 90.00%/95.00%)"),
                Metric("aws_rds_replication_slot_disk_usage", 100.0, levels=(90.0, 95.0)),
            ],
            id="If the ReplicationSlotDiskUsage levels are above the warn levels, the check state will be CRIT with a appropriate description.",
        ),
    ],
)
def test_check_aws_rds_replication_slot_usage(
    section: Mapping[str, Mapping[str, float]],
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replication_slot_usage")]

    check_result = list(
        check.check_function(
            item="disk",
            params=params,
            section=section,
        )
    )
    assert check_result[0] == Result(
        state=State.OK, summary="60 B"
    )  # The first result is always OK and shows the information about the ReplicationSlotDiskUsage in Bytes
    assert check_result == expected_check_result
