#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State, TableRow
from cmk.base.plugins.agent_based.oracle_dataguard_stats import (
    inventory_oracle_dataguard_stats,
    parse_oracle_dataguard_stats,
)

from .utils_inventory import sort_inventory_result

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
def test_discover_oracle_dataguard_stats(fix_register, string_table, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_dataguard_stats")]
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
                Result(state=State.OK, summary="Apply finish time: 17.0 s"),
                Metric("apply_finish_time", 17.0),
                Result(state=State.OK, summary="Apply lag: 28 m"),
                Metric("apply_lag", 1737.0),
                Result(state=State.OK, summary="Transport lag: 0.00 s"),
                Metric("transport_lag", 0.0),
            ],
        ),
        (
            _AGENT_OUTPUT,
            "KNULF.TUXSTDB",
            [
                Result(state=State.OK, summary="Database Role physical standby"),
                Result(state=State.OK, summary="Apply finish time: 17.0 s"),
                Metric("apply_finish_time", 17.0),
                Result(state=State.CRIT, summary="Apply lag: no value"),
                Result(state=State.OK, summary="Transport lag: 0.00 s"),
                Metric("transport_lag", 0.0),
                Result(state=State.OK, summary="old plugin data found, recovery active?"),
            ],
        ),
    ],
)
def test_check_oracle_dataguard_stats(fix_register, string_table, item, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_dataguard_stats")]
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
def test_inventory_oracle_dataguard_stats(string_table, expected_result) -> None:
    assert sort_inventory_result(
        inventory_oracle_dataguard_stats(parse_oracle_dataguard_stats(string_table))
    ) == sort_inventory_result(expected_result)
