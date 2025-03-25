#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.unit.cmk.plugins.oracle.agent_based.utils_inventory import sort_inventory_result

from cmk.checkengine.plugins import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    InventoryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.oracle.agent_based.oracle_dataguard_stats import (
    inventory_oracle_dataguard_stats,
    parse_oracle_dataguard_stats,
)

_AGENT_OUTPUT = [
    [
        "TESTDB",
        "TESTDBU2",
        "PHYSICAL STANDBYapply finish time",
        "+00 00:00:00.000",
        "NOT ALLOWED",
        "ENABLED",
        "MAXIMUM",
        "PERFORMANCE",
        "DISABLED",
        "",
        "",
        "",
        "APPLYING_LOG",
    ],
    ["TUX12C", "TUXSTDB", "PHYSICAL STANDBY", "transport lag", "+00 00:00:00"],
    ["TUX12C", "TUXSTDB", "PHYSICAL STANDBY", "apply lag", "+00 00:28:57"],
    ["TUX12C", "TUXSTDB", "PHYSICAL STANDBY", "apply finish time", "+00 00:00:17.180"],
    ["TUX12C", "TUXSTDB", "PHYSICAL STANDBY", "estimated startup time", "20"],
    ["KNULF", "TUXSTDB", "PHYSICAL STANDBY", "transport lag", "+00 00:00:00"],
    ["KNULF", "TUXSTDB", "PHYSICAL STANDBY", "apply lag", ""],
    ["KNULF", "TUXSTDB", "PHYSICAL STANDBY", "apply finish time", "+00 00:00:17.180"],
    ["KNULF", "TUXSTDB", "PHYSICAL STANDBY", "estimated startup time", "20"],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT,
            [
                Service(item="KNULF.TUXSTDB"),
                Service(item="TESTDB.TESTDBU2"),
                Service(item="TUX12C.TUXSTDB"),
            ],
        ),
    ],
)
def test_discover_oracle_dataguard_stats(
    agent_based_plugins: AgentBasedPlugins,
    string_table: StringTable,
    expected_result: DiscoveryResult,
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("oracle_dataguard_stats")]
    section = parse_oracle_dataguard_stats(string_table)
    assert sorted(check_plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            _AGENT_OUTPUT,
            "TESTDB.TESTDBU2",
            [
                Result(state=State.OK, summary="Database Role physical standbyapply finish time"),
                Result(state=State.OK, summary="Protection Mode performance"),
                Result(state=State.OK, summary="Broker maximum"),
            ],
        ),
        (
            _AGENT_OUTPUT,
            "TUX12C.TUXSTDB",
            [
                Result(state=State.OK, summary="Database Role physical standby"),
                Result(state=State.OK, summary="Apply finish time: 17 seconds"),
                Metric("apply_finish_time", 17.0),
                Result(state=State.OK, summary="Apply lag: 28 minutes 57 seconds"),
                Metric("apply_lag", 1737.0),
                Result(state=State.OK, summary="Transport lag: 0 seconds"),
                Metric("transport_lag", 0.0),
            ],
        ),
        (
            _AGENT_OUTPUT,
            "KNULF.TUXSTDB",
            [
                Result(state=State.OK, summary="Database Role physical standby"),
                Result(state=State.OK, summary="Apply finish time: 17 seconds"),
                Metric("apply_finish_time", 17.0),
                Result(state=State.CRIT, summary="Apply lag: no value"),
                Result(state=State.OK, summary="Transport lag: 0 seconds"),
                Metric("transport_lag", 0.0),
                Result(state=State.OK, summary="old plug-in data found, recovery active?"),
            ],
        ),
    ],
)
def test_check_oracle_dataguard_stats(
    agent_based_plugins: AgentBasedPlugins,
    string_table: StringTable,
    item: str,
    expected_result: CheckResult,
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("oracle_dataguard_stats")]
    section = parse_oracle_dataguard_stats(string_table)
    assert (
        list(
            check_plugin.check_function(
                item=item, params={"missing_apply_lag_state": 2}, section=section
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
                    path=["software", "applications", "oracle", "dataguard_stats"],
                    key_columns={
                        "sid": "TESTDB",
                        "db_unique": "TESTDB.TESTDBU2",
                    },
                    inventory_columns={
                        "role": "PHYSICAL STANDBYapply finish time",
                        "switchover": "ENABLED",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "oracle", "dataguard_stats"],
                    key_columns={
                        "sid": "TUX12C",
                        "db_unique": "TUX12C.TUXSTDB",
                    },
                    inventory_columns={
                        "role": "PHYSICAL STANDBY",
                        "switchover": None,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "oracle", "dataguard_stats"],
                    key_columns={
                        "sid": "KNULF",
                        "db_unique": "KNULF.TUXSTDB",
                    },
                    inventory_columns={
                        "role": "PHYSICAL STANDBY",
                        "switchover": None,
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_oracle_dataguard_stats(
    string_table: StringTable, expected_result: InventoryResult
) -> None:
    assert sort_inventory_result(
        inventory_oracle_dataguard_stats(parse_oracle_dataguard_stats(string_table))
    ) == sort_inventory_result(expected_result)
