#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import graylog_failures

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

_STRING_TABLE_MSG_STR = [
    [
        '{"count": 5963, "failures": [{"timestamp": "2022-08-08T08:33:26.622Z", "letter_id": "c9d31a87-16f4-11ed-b805-001a4a1078b5", '
        '"message": "ElasticsearchException[Elasticsearch exception [type=mapper_parsing_exception, reason=Could not dynamically add mapping '
        'for field [app.kubernetes.io/component]. Existing mapping for [kubernetes_labels.app] must be of type object but found [keyword].]]", '
        '"index": "graylog_9375", "type": "indexing"}, {"timestamp": "2022-08-08T08:33:25.031Z", "letter_id": "c9d2f37d-16f4-11ed-b805-001a4a1078b5", '
        '"message": "ElasticsearchException[Elasticsearch exception [type=mapper_parsing_exception, reason=Could not dynamically add mapping for field '
        '[app.kubernetes.io/component]. Existing mapping for [kubernetes_labels.app] must be of type object but found [keyword].]]", "index": "graylog_9375", '
        '"type": "indexing"}], "total": 131346, "ds_param_since": 1800}'
    ]
]


def test_parse_no_failures() -> None:
    assert graylog_failures.parse(_STRING_TABLE_NO_FAILURES) == graylog_failures.Section(
        failures=None, total=131346, count=0, ds_param_since=1800.0
    )


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
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
        pytest.param(
            _STRING_TABLE_MSG_STR,
            [Service()],
            id="failure messages are non-json strings",
        ),
    ],
)
def test_discover(
    string_table: StringTable,
    expected_result: DiscoveryResult,
) -> None:
    section = graylog_failures.parse(string_table)
    assert list(graylog_failures.discover(section)) == expected_result


@pytest.mark.parametrize(
    ["string_table", "params", "expected_result"],
    [
        pytest.param(
            _STRING_TABLE_ZERO_FAILURES,
            {},
            [
                Result(state=State.OK, summary="Total number of failures: 198508"),
                Metric("failures", 198508.0),
                Result(state=State.OK, summary="Failures in last 30 minutes 0 seconds: 0"),
            ],
            id="zero failures",
        ),
        pytest.param(
            _STRING_TABLE_MSG_DICT,
            {},
            [
                Result(state=State.OK, summary="Total number of failures: 198508"),
                Metric("failures", 198508.0),
                Result(state=State.OK, summary="Failures in last 30 minutes 0 seconds: 6"),
                Result(
                    state=State.OK,
                    summary="Affected indices: 3, see service details for further information",
                ),
                Result(
                    state=State.OK,
                    notice="Timestamp: 2019-09-20T10:52:02.908Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];",
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
                    summary="Failures in last 30 minutes 0 seconds: 6 (warn/crit at 1/10)",
                ),
                Result(
                    state=State.OK,
                    summary="Affected indices: 3, see service details for further information",
                ),
                Result(
                    state=State.OK,
                    notice="Timestamp: 2019-09-20T10:52:02.908Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:02.908Z, Index: graylog_index1, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: a, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];\nTimestamp: 2019-09-20T10:52:03.110Z, Index: b, Type: cluster_block_exception, Reason: blocked by: [SERVICE_UNAVAILABLE/2/no master];",
                ),
            ],
            id="failure messages are json-serialized dicts, with levels on number of failures",
        ),
        pytest.param(
            _STRING_TABLE_MSG_STR,
            {},
            [
                Result(state=State.OK, summary="Total number of failures: 131346"),
                Metric("failures", 131346.0),
                Result(state=State.OK, summary="Failures in last 30 minutes 0 seconds: 5963"),
                Result(
                    state=State.OK,
                    summary="Affected indices: 1, see service details for further information",
                ),
                Result(
                    state=State.OK,
                    notice="Timestamp: 2022-08-08T08:33:25.031Z, Index: graylog_9375, Message: ElasticsearchException[Elasticsearch exception [type=mapper_parsing_exception, reason=Could not dynamically add mapping for field [app.kubernetes.io/component]. Existing mapping for [kubernetes_labels.app] must be of type object but found [keyword].]]\nTimestamp: 2022-08-08T08:33:26.622Z, Index: graylog_9375, Message: ElasticsearchException[Elasticsearch exception [type=mapper_parsing_exception, reason=Could not dynamically add mapping for field [app.kubernetes.io/component]. Existing mapping for [kubernetes_labels.app] must be of type object but found [keyword].]]",
                ),
            ],
            id="failure messages are non-json strings",
        ),
    ],
)
def test_check(
    string_table: StringTable,
    params: Mapping[str, tuple[int, int] | None],
    expected_result: CheckResult,
) -> None:
    section = graylog_failures.parse(string_table)
    assert (
        list(
            graylog_failures.check(
                params=params,
                section=section,
            )
        )
        == expected_result
    )
