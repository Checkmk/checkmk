#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import AgentSectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

_STRING_TABLE_NO_FAILURES = [['{"count": 0, "ds_param_since": 1800, "total": 131346}']]

_STRING_TABLE_ZERO_FAILURES = [
    ['{"failures": [], "count": 0, "ds_param_since": 1800, "total": 198508}']
]

_STRING_TABLE_MSG_DICT = [
    [
        '{"failures": [{"timestamp": "2019-09-20T10:52:03.110Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: '
        '[SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "a", "type": "message", "letter_id": "ae66b494-db94-11e9-9de2-005056981acf"}, {"timestamp": '
        '"2019-09-20T10:52:03.110Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", '
        '"index": "b", "type": "message", "letter_id": "ae66b493-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", "message": '
        '"{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "b", "type": "message", '
        '"letter_id": "ae66b48f-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: '
        '[SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "a", "type": "message", "letter_id": "ae66b48b-db94-11e9-9de2-005056981acf"}, {"timestamp": '
        '"2019-09-20T10:52:02.908Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", '
        '"index": "graylog_index1", "type": "message", "letter_id": "ae66b487-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", '
        '"message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "graylog_index1", '
        '"type": "message", "letter_id": "ae66b485-db94-11e9-9de2-005056981acf"}], "count": 6, "ds_param_since": 1800, "total": 198508}'
    ]
]


@pytest.fixture(name="section_plugin", scope="module")
def fixture_section_plugin(fix_register: FixRegister) -> AgentSectionPlugin:
    return fix_register.agent_sections[SectionName("graylog_failures")]


@pytest.fixture(name="check_plugin", scope="module")
def fixture_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("graylog_failures")]


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            _STRING_TABLE_NO_FAILURES,
            [],
            id="no failures",
        ),
        pytest.param(
            _STRING_TABLE_ZERO_FAILURES,
            [Service()],
            id="zero failures",
        ),
        pytest.param(
            _STRING_TABLE_MSG_DICT,
            [Service()],
            id="failure messages are json-serialized dicts",
        ),
    ],
)
def test_discover(
    section_plugin: AgentSectionPlugin,
    check_plugin: CheckPlugin,
    string_table: StringTable,
    expected_result: DiscoveryResult,
) -> None:
    assert (
        list(check_plugin.discovery_function(section_plugin.parse_function(string_table)))
        == expected_result
    )


@pytest.mark.parametrize(
    ["string_table", "params", "expected_result"],
    [
        pytest.param(
            _STRING_TABLE_NO_FAILURES,
            {},
            [],
            id="no failures",
        ),
        pytest.param(
            _STRING_TABLE_ZERO_FAILURES,
            {},
            [
                Result(state=State.OK, summary="Total number of failures: 198508"),
                Metric("failures", 198508.0),
                Result(state=State.OK, summary="Failures in last 30 m: 0"),
            ],
            id="zero failures",
        ),
        pytest.param(
            _STRING_TABLE_MSG_DICT,
            {},
            [
                Result(state=State.OK, summary="Total number of failures: 198508"),
                Metric("failures", 198508.0),
                Result(state=State.OK, summary="Failures in last 30 m: 6"),
                Result(
                    state=State.OK,
                    summary="Affected indices: 3, See long output for further information",
                ),
                Result(
                    state=State.OK,
                    summary="6 additional details available",
                    details="Timestamp: 2019-09-20T10:52:02.908Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];",
                ),
            ],
            id="failure messages are json-serialized dicts",
        ),
        pytest.param(
            _STRING_TABLE_MSG_DICT,
            {
                "failures": (5000, 2000),
                "failures_last": (1, 10),
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Total number of failures: 198508 (warn/crit at 5000/2000)",
                ),
                Metric("failures", 198508.0, levels=(5000.0, 2000.0)),
                Result(
                    state=State.WARN,
                    summary="Failures in last 30 m: 6 (warn/crit at 1/10)",
                ),
                Result(
                    state=State.OK,
                    summary="Affected indices: 3, See long output for further information",
                ),
                Result(
                    state=State.OK,
                    summary="6 additional details available",
                    details="Timestamp: 2019-09-20T10:52:02.908Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];",
                ),
            ],
            id="failure messages are json-serialized dicts, with levels on number of failures",
        ),
    ],
)
def test_check(
    section_plugin: AgentSectionPlugin,
    check_plugin: CheckPlugin,
    string_table: StringTable,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_plugin.check_function(
                params=params,
                section=section_plugin.parse_function(string_table),
            )
        )
        == expected_result
    )
