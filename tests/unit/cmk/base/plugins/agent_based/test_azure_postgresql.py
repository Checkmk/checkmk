#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.azure_postgresql import check_replication
from cmk.base.plugins.agent_based.utils.azure import AzureMetric, Resource, Section


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            {
                "checkmk-postgresql-server": Resource(
                    id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforPostgreSQL/servers/checkmk-postgresql-server",
                    name="checkmk-postgresql-server",
                    type="Microsoft.DBforPostgreSQL/servers",
                    group="BurningMan",
                    location="westeurope",
                    metrics={
                        "maximum_pg_replica_log_delay_in_seconds": AzureMetric(
                            name="pg_replica_log_delay_in_seconds",
                            aggregation="maximum",
                            value=2.0,
                            unit="seconds",
                        ),
                    },
                )
            },
            "checkmk-postgresql-server",
            {"levels": (1.0, 5.0)},
            [
                Result(
                    state=State.WARN,
                    summary="Replication lag: 2 seconds (warn/crit at 1 second/5 seconds)",
                ),
                Metric("replication_lag", 2.0, levels=(1.0, 5.0)),
            ],
        ),
    ],
)
def test_check_replication(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_replication()(item, params, section)) == expected_result
