#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.graylog_cluster_traffic import (
    check_graylog_cluster_traffic,
    discover_graylog_cluster_traffic,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"from": "2025-05-08T00:00:00.000Z", "to": "2025-05-09T14:25:49.119Z", "input": {"2025-05-08T01:00:00.000Z": 12092135417, "2025-05-09T14:00:00.000Z": 827199820}, "output": {"2025-05-08T01:00:00.000Z": 11784754125, "2025-05-09T14:00:00.000Z": 4806152524}, "decoded": {"2025-05-08T01:00:00.000Z": 7472273714, "2025-05-09T14:00:00.000Z": 3076174718}}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_graylog_cluster_traffic_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for graylog_cluster_traffic regression test."""
    parsed = deserialize_and_merge_json(string_table)
    result = list(discover_graylog_cluster_traffic(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_metrics_names",
    [
        (
            None,
            {},
            [
                [
                    '{"from": "2025-05-08T00:00:00.000Z", "to": "2025-05-09T14:25:49.119Z", "input": {"2025-05-08T01:00:00.000Z": 12092135417, "2025-05-09T14:00:00.000Z": 827199820}, "output": {"2025-05-08T01:00:00.000Z": 11784754125, "2025-05-09T14:00:00.000Z": 4806152524}, "decoded": {"2025-05-08T01:00:00.000Z": 7472273714, "2025-05-09T14:00:00.000Z": 3076174718}}'
                ]
            ],
            ["graylog_input", "graylog_output", "graylog_decoded"],  # Expected metric names
        ),
    ],
)
def test_check_graylog_cluster_traffic_regression(
    item: None,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_metrics_names: list[str],
) -> None:
    """Test check function for graylog_cluster_traffic regression test."""
    parsed = deserialize_and_merge_json(string_table)
    result = list(check_graylog_cluster_traffic(item, params, parsed))

    # Check that we get results for input, output, decoded, and last updated
    assert len(result) == 4

    # Check that we have the expected metrics in the results
    found_metrics = set()
    for check_result in result:
        if len(check_result) >= 3 and isinstance(check_result[2], list):
            for metric in check_result[2]:
                if isinstance(metric, tuple) and len(metric) >= 1:
                    found_metrics.add(metric[0])

    for expected_metric in expected_metrics_names:
        assert expected_metric in found_metrics, (
            f"Expected metric '{expected_metric}' not found in results"
        )

    # Check that last result contains "Last updated" information
    last_result = result[-1]
    assert "Last updated" in str(last_result[1]), (
        f"Expected 'Last updated' info in last result: {last_result}"
    )
