#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import (
    CheckResult,
    Result,
    State,
    StringTable,
)

STRING_TABLE_OK = [
    [["TS3100", "IBM", "F.01"]],
    [["3"]],
    [["1", "3", "L2U7777777", "2", "0", "0", "No error"]],
    [["1", "99WT888888", "0", "0", "0", "0"]],
]

STRING_TABLE_NOK = [
    [["TS3100", "IBM", "F.01"]],
    [["5"]],
    [["1", "4", "L2U7777777", "2", "0", "0", "No error"]],
    [["1", "99WT888888", "1", "2", "3", "4"]],
]


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="IBM TS3100, Version F.01")],
            id="ok",
        ),
    ],
)
def test_ibm_storage_ts_info(
    agent_based_plugins: AgentBasedPlugins,
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("ibm_storage_ts")]
    assert (
        list(plugin.check_function(section=string_table, item=None, params={})) == expected_result
    )


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="Device Status: Ok")],
            id="ok",
        ),
        pytest.param(
            STRING_TABLE_NOK,
            [Result(state=State.CRIT, summary="Device Status: critical")],
            id="nok",
        ),
    ],
)
def test_ibm_storage_ts_status(
    agent_based_plugins: AgentBasedPlugins,
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("ibm_storage_ts_status")]
    assert (
        list(plugin.check_function(section=string_table, item=None, params={})) == expected_result
    )


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="Device L2U7777777, Status: Ok, Drives: 2")],
            id="ok",
        ),
        pytest.param(
            STRING_TABLE_NOK,
            [
                Result(
                    state=State.WARN, summary="Device L2U7777777, Status: non-critical, Drives: 2"
                )
            ],
            id="nok",
        ),
    ],
)
def test_ibm_storage_ts_library(
    agent_based_plugins: AgentBasedPlugins,
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("ibm_storage_ts_library")]
    assert list(plugin.check_function(section=string_table, item="1", params={})) == expected_result


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="S/N: 99WT888888")],
            id="ok",
        ),
        pytest.param(
            STRING_TABLE_NOK,
            [
                Result(state=State.OK, summary="S/N: 99WT888888"),
                Result(state=State.CRIT, summary="2 hard write errors"),
                Result(state=State.WARN, summary="1 recovered write errors"),
                Result(state=State.CRIT, summary="4 hard read errors"),
                Result(state=State.WARN, summary="3 recovered read errors"),
            ],
            id="nok",
        ),
    ],
)
def test_ibm_storage_ts_drive(
    agent_based_plugins: AgentBasedPlugins,
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("ibm_storage_ts_drive")]
    assert list(plugin.check_function(section=string_table, item="1", params={})) == expected_result
