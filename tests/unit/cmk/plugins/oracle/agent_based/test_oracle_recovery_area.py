#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    InventoryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName
from cmk.plugins.oracle.agent_based.oracle_recovery_area import (
    inventory_oracle_recovery_area,
)

_AGENT_OUTPUT = [
    ["AIMDWHD1", "300", "51235", "49000", "300"],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT,
            [
                Service(item="AIMDWHD1"),
            ],
        ),
    ],
)
def test_discover_oracle_recovery_area(
    agent_based_plugins: AgentBasedPlugins,
    string_table: StringTable,
    expected_result: Sequence[Service],
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("oracle_recovery_area")]
    assert sorted(check_plugin.discovery_function(string_table)) == expected_result


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            _AGENT_OUTPUT,
            "AIMDWHD1",
            [
                Result(
                    state=State.CRIT,
                    summary="47.9 GiB out of 50.0 GiB used (95.1%, warn/crit at 70.0%/90.0%), 300 MiB reclaimable",
                ),
                Metric("used", 49000.0, levels=(35864.5, 46111.5), boundaries=(0.0, 51235.0)),
                Metric("reclaimable", 300.0),
            ],
        ),
    ],
)
def test_check_oracle_recovery_area(
    agent_based_plugins: AgentBasedPlugins,
    string_table: StringTable,
    item: str,
    expected_result: CheckResult,
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("oracle_recovery_area")]
    assert (
        list(
            check_plugin.check_function(
                item=item,
                params={
                    "levels": (70.0, 90.0),
                },
                section=string_table,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            _AGENT_OUTPUT,
            [
                TableRow(
                    path=["software", "applications", "oracle", "recovery_area"],
                    key_columns={
                        "sid": "AIMDWHD1",
                    },
                    inventory_columns={
                        "flashback": "300",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_oracle_recovery_area(
    string_table: StringTable, expected_result: InventoryResult
) -> None:
    assert list(inventory_oracle_recovery_area(string_table)) == expected_result
