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
            {"disk": {"ReplicaLag": 10.0}},
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
def test_aws_rds_replica_lag_discovery(
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replica_lag")]
    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_rds_replica_lag_item_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replica_lag")]
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


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"disk": {"ReplicaLag": 10.0}},
            {"lag_levels": (60, 120)},
            [
                Result(state=State.OK, summary="Lag: 10 seconds"),
                Metric("aws_rds_replica_lag", 10.0, levels=(60.0, 120.0)),
            ],
            id="If the levels are below the warn/crit levels, the check state will be OK with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"ReplicaLag": 92.0}},
            {"lag_levels": (60, 120)},
            [
                Result(
                    state=State.WARN,
                    summary="Lag: 1 minute 32 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
                ),
                Metric("aws_rds_replica_lag", 92.0, levels=(60.0, 120.0)),
            ],
            id="If the levels are above the warn levels, the check state will be WARN with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"ReplicaLag": 125.0}},
            {"lag_levels": (60, 120)},
            [
                Result(
                    state=State.CRIT,
                    summary="Lag: 2 minutes 5 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
                ),
                Metric("aws_rds_replica_lag", 125.0, levels=(60.0, 120.0)),
            ],
            id="If the levels are above the crit levels, the check state will be CRIT with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"ReplicaLag": 125.0, "OldestReplicationSlotLag": 120}},
            {"lag_levels": (60, 120)},
            [
                Result(
                    state=State.CRIT,
                    summary="Lag: 2 minutes 5 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
                ),
                Metric("aws_rds_replica_lag", 125.0, levels=(60.0, 120.0)),
                Result(state=State.OK, summary="Oldest replication slot lag: 120 B"),
                Metric("aws_rds_oldest_replication_slot_lag", 120.0),
            ],
            id="If OldestReplicationSlotLag is present in the metric, a check is executed for this metric as well. The OldestReplicationSlotLag levels are compared to the warn/crit levels from the rule and the appropriate result is given.",
        ),
    ],
)
def test_check_aws_rds_replica_lag(
    section: Mapping[str, Mapping[str, float]],
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_replica_lag")]

    check_result = list(
        check.check_function(
            item="disk",
            params=params,
            section=section,
        )
    )
    assert check_result == expected_check_result
