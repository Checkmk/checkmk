#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.base.legacy_checks.mssql_connections import (
    CheckParams,
    inventory_mssql_connections,
    MSSQLConnections,
    parse_mssql_connections,
)
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPlugin, CheckPluginName

# TODO: Enable mypy rule after plugin migration
# mypy: disable-error-code="no-untyped-call"


@pytest.fixture
def check_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName("mssql_connections")]


STRING_TABLE = [
    ["FOO", "DBa", "25"],
    ["FOO", "DBb", "0"],
]


@pytest.mark.parametrize(
    ["string_table", "expected"],
    [
        pytest.param(
            STRING_TABLE,
            MSSQLConnections(
                {
                    "FOO DBa": 25,
                    "FOO DBb": 0,
                }
            ),
            id="good input",
        ),
        pytest.param(
            [["BAD", "LINE"]],
            MSSQLConnections({}),
            id="no input",
        ),
    ],
)
def test_parse_mssql_connections(string_table: StringTable, expected: MSSQLConnections) -> None:
    parsed = parse_mssql_connections(string_table)
    assert parsed == expected


def test_inventory_mssql_connections() -> None:
    section = parse_mssql_connections(STRING_TABLE)
    assert {service.item for service in inventory_mssql_connections(section)} == {
        "FOO DBa",
        "FOO DBb",
    }


@pytest.mark.parametrize(
    ["item", "params", "string_table", "expected_results"],
    [
        pytest.param(
            "FOO DBa",
            CheckParams(levels=None),
            STRING_TABLE,
            [Result(state=State.OK, summary="Connections: 25"), Metric("connections", 25.0)],
        ),
        pytest.param(
            "FOO DBa",
            CheckParams(levels=(20, 30)),
            STRING_TABLE,
            [
                Result(state=State.WARN, summary="Connections: 25 (warn/crit at 20/30)"),
                Metric("connections", 25.0, levels=(20.0, 30.0)),
            ],
        ),
        pytest.param(
            "FOO DBa",
            CheckParams(levels=(10, 20)),
            STRING_TABLE,
            [
                Result(state=State.CRIT, summary="Connections: 25 (warn/crit at 10/20)"),
                Metric("connections", 25.0, levels=(10.0, 20.0)),
            ],
        ),
        pytest.param("FOO DBc", {"levels": None}, STRING_TABLE, []),
    ],
)
def test_check_mssql_connections(
    check_plugin: CheckPlugin,
    item: str,
    params: Mapping[str, object],
    string_table: StringTable,
    expected_results: list[Result],
) -> None:
    section = parse_mssql_connections(string_table)
    assert (
        list(check_plugin.check_function(item=item, params=params, section=section))
        == expected_results
    )
