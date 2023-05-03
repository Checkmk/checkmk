#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable


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
    fix_register: FixRegister, string_table: StringTable, expected_result: CheckResult
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("aws_elb")]
    result = list(check_plugin.check_function(item=None, params={}, section=string_table))
    assert result == expected_result
