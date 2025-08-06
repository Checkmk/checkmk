#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from contextlib import suppress

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.db2.agent_based.db2_counters import (
    _check_db2_counters,
    discover_db2_counters,
    parse_db2_counters,
    Section,
)

STRING_TABLE = [
    ["TIMESTAMP", "1426610723"],
    ["db2taddm:CMDBS1", "deadlocks", "0"],
    ["db2taddm:CMDBS1", "lockwaits", "99"],
    ["db2taddm:CMDBS1", "sortoverflows", "2387"],
    ["TIMESTAMP", "1426610763"],
    ["db2taddm:CMDBS6", "deadlocks", "99"],
    ["db2taddm:CMDBS6", "lockwaits", "91"],
    ["db2taddm:CMDBS6", "sortoverflows", "237"],
    ["Example", "for", "database", "in", "DPF", "mode", "##"],
    ["TIMESTAMP", "1439976757"],
    ["db2ifa:DDST1", "node", "0", "iasv0091", "0"],
    ["db2ifa:DDST1", "node", "1", "iasv0091", "1"],
    ["db2ifa:DDST1", "node", "2", "iasv0091", "2"],
    ["db2ifa:DDST1", "node", "3", "iasv0091", "3"],
    ["db2ifa:DDST1", "node", "4", "iasv0091", "4"],
    ["db2ifa:DDST1", "node", "5", "iasv0091", "5"],
    ["db2ifa:DDST1", "deadlocks", "0"],
    ["db2ifa:DDST1", "deadlocks", "0"],
    ["db2ifa:DDST1", "deadlocks", "0"],
    ["db2ifa:DDST1", "deadlocks", "0"],
    ["db2ifa:DDST1", "deadlocks", "0"],
    ["db2ifa:DDST1", "deadlocks", "0"],
    ["db2ifa:DDST1", "lockwaits", "0"],
    ["db2ifa:DDST1", "lockwaits", "0"],
    ["db2ifa:DDST1", "lockwaits", "0"],
    ["db2ifa:DDST1", "lockwaits", "0"],
    ["db2ifa:DDST1", "lockwaits", "0"],
    ["db2ifa:DDST1", "lockwaits", "80"],
]


@pytest.mark.parametrize(
    "string_table,expected",
    [
        (
            STRING_TABLE,
            (
                1439976757,
                {
                    "db2ifa:DDST1 DPF 0 iasv0091 0": {
                        "TIMESTAMP": 1439976757,
                        "deadlocks": "0",
                        "lockwaits": "0",
                    },
                    "db2ifa:DDST1 DPF 1 iasv0091 1": {
                        "TIMESTAMP": 1439976757,
                        "deadlocks": "0",
                        "lockwaits": "0",
                    },
                    "db2ifa:DDST1 DPF 2 iasv0091 2": {
                        "TIMESTAMP": 1439976757,
                        "deadlocks": "0",
                        "lockwaits": "0",
                    },
                    "db2ifa:DDST1 DPF 3 iasv0091 3": {
                        "TIMESTAMP": 1439976757,
                        "deadlocks": "0",
                        "lockwaits": "0",
                    },
                    "db2ifa:DDST1 DPF 4 iasv0091 4": {
                        "TIMESTAMP": 1439976757,
                        "deadlocks": "0",
                        "lockwaits": "0",
                    },
                    "db2ifa:DDST1 DPF 5 iasv0091 5": {
                        "TIMESTAMP": 1439976757,
                        "deadlocks": "0",
                        "lockwaits": "80",
                    },
                    "db2taddm:CMDBS1": {
                        "TIMESTAMP": 1426610723,
                        "deadlocks": "0",
                        "lockwaits": "99",
                    },
                    "db2taddm:CMDBS6": {
                        "TIMESTAMP": 1426610763,
                        "deadlocks": "99",
                        "lockwaits": "91",
                    },
                },
            ),
        ),
    ],
)
def test_parse_db2_counters(string_table: StringTable, expected: Section) -> None:
    assert parse_db2_counters(string_table) == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            STRING_TABLE,
            [
                Service(item="db2taddm:CMDBS1"),
                Service(item="db2taddm:CMDBS6"),
                Service(item="db2ifa:DDST1 DPF 0 iasv0091 0"),
                Service(item="db2ifa:DDST1 DPF 1 iasv0091 1"),
                Service(item="db2ifa:DDST1 DPF 2 iasv0091 2"),
                Service(item="db2ifa:DDST1 DPF 3 iasv0091 3"),
                Service(item="db2ifa:DDST1 DPF 4 iasv0091 4"),
                Service(item="db2ifa:DDST1 DPF 5 iasv0091 5"),
            ],
        ),
    ],
)
def test_discover_db2_counters(string_table: list[list[str]], expected: DiscoveryResult) -> None:
    section = parse_db2_counters(string_table)
    assert list(discover_db2_counters(section)) == expected


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Deadlocks: 1.1/s"),
                Metric("deadlocks", 1.1),
                Result(state=State.OK, summary="Lockwaits: 2.0/s"),
                Metric("lockwaits", 2.0),
            ],
            id="no levels",
        ),
        pytest.param(
            {"deadlocks": (1.0, 2.0)},
            [
                Result(state=State.WARN, summary="Deadlocks: 1.1/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("deadlocks", 1.1, levels=(1.0, 2.0)),
                Result(state=State.OK, summary="Lockwaits: 2.0/s"),
                Metric("lockwaits", 2.0),
            ],
            id="warn",
        ),
        pytest.param(
            {"lockwaits": (0.1, 0.2)},
            [
                Result(state=State.OK, summary="Deadlocks: 1.1/s"),
                Metric("deadlocks", 1.1),
                Result(state=State.CRIT, summary="Lockwaits: 2.0/s (warn/crit at 0.1/s/0.2/s)"),
                Metric("lockwaits", 2.0, levels=(0.1, 0.2)),
            ],
            id="crit",
        ),
    ],
)
def test_check_db2_counters(
    params: Mapping[str, tuple[float, float]], expected: CheckResult
) -> None:
    # Assemble
    string_table_1 = [
        ["TIMESTAMP", "1426610763"],
        ["db2taddm:CMDBS6", "deadlocks", "99"],
        ["db2taddm:CMDBS6", "lockwaits", "91"],
        ["db2taddm:CMDBS6", "sortoverflows", "237"],
    ]

    string_table_2 = [
        ["TIMESTAMP", "1426610823"],
        ["db2taddm:CMDBS6", "deadlocks", "165"],
        ["db2taddm:CMDBS6", "lockwaits", "211"],
        ["db2taddm:CMDBS6", "sortoverflows", "237"],
    ]
    section_1 = parse_db2_counters(string_table_1)
    section_2 = parse_db2_counters(string_table_2)
    value_store: dict[str, object] = {}
    with suppress(IgnoreResultsError):
        list(_check_db2_counters(value_store, "db2taddm:CMDBS6", params, section_1))
    # Act
    results = list(_check_db2_counters(value_store, "db2taddm:CMDBS6", params, section_2))
    # Assert
    assert results == expected
