#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.plugins import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            {
                "RequestCount": 693.235,
                "SurgeQueueLength": 1024.0,
                "SpilloverCount": 0.058333333333333334,
                "Latency": 4.2748083637903225e-06,
                "HealthyHostCount": 1.8,
                "UnHealthyHostCount": 0.0,
                "BackendConnectionErrors": 0.058333333333333334,
            },
            [
                Result(state=State.OK, summary="Surge queue length: 1024"),
                Metric("aws_surge_queue_length", 1024.0),
                Result(state=State.OK, summary="Spillover: 0.058/s"),
                Metric("aws_spillover", 0.058333333333333334),
            ],
        )
    ],
)
def test_check_aws_elb_statistics(
    agent_based_plugins: AgentBasedPlugins, string_table: StringTable, expected_result: CheckResult
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("aws_elb")]
    result = list(check_plugin.check_function(item=None, params={}, section=string_table))
    assert result == expected_result
