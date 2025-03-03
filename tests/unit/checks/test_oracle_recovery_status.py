#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, Result, State


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "Error Message:          MyDatabase",
            [
                [
                    "Error Message:          MyDatabase",
                    "FAILURE",
                    "ERROR: ORA-123456: Some kind of error occurred",
                ]
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Error Message:          MyDatabase, FAILURE, ERROR: ORA-123456: Some kind of error occurred",
                )
            ],
        )
    ],
)
def test_check_oracle_recovery_status(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    info: list[list[str]],
    expected_result: CheckResult,
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("oracle_recovery_status")]
    result = list(check_plugin.check_function(item=item, params={}, section=info))
    assert result == expected_result
