#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


from cmk.agent_based.v2 import Metric, Service
from cmk.legacy_checks.graylog_cluster_traffic import (
    check_graylog_cluster_traffic,
    discover_graylog_cluster_traffic,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json

_SECTION = [
    [
        '{"from": "2025-05-08T00:00:00.000Z", "to": "2025-05-09T14:25:49.119Z", "input": {"2025-05-08T01:00:00.000Z": 12092135417, "2025-05-09T14:00:00.000Z": 827199820}, "output": {"2025-05-08T01:00:00.000Z": 11784754125, "2025-05-09T14:00:00.000Z": 4806152524}, "decoded": {"2025-05-08T01:00:00.000Z": 7472273714, "2025-05-09T14:00:00.000Z": 3076174718}}'
    ]
]


def test_discover_graylog_cluster_traffic_regression() -> None:
    parsed = deserialize_and_merge_json(_SECTION)
    assert list(discover_graylog_cluster_traffic(parsed)) == [Service()]


def test_check_graylog_cluster_traffic_regression() -> None:
    parsed = deserialize_and_merge_json(_SECTION)
    results = list(check_graylog_cluster_traffic({}, parsed))

    metric_names = {r.name for r in results if isinstance(r, Metric)}
    assert {"graylog_input", "graylog_output", "graylog_decoded"} <= metric_names
    assert any("Last updated" in getattr(r, "summary", "") for r in results), (
        f"Expected 'Last updated' info in results: {results}"
    )
