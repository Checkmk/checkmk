#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
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


def test_discover_graylog_cluster_traffic() -> None:
    parsed = deserialize_and_merge_json(_SECTION)
    assert list(discover_graylog_cluster_traffic(parsed)) == [Service()]


def test_check_graylog_cluster_traffic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    parsed = deserialize_and_merge_json(_SECTION)
    assert list(check_graylog_cluster_traffic({}, parsed)) == [
        Result(state=State.OK, summary="Input: 789 MiB"),
        Metric("graylog_input", 827199820),
        Result(state=State.OK, summary="Output: 4.48 GiB"),
        Metric("graylog_output", 4806152524),
        Result(state=State.OK, summary="Decoded: 2.86 GiB"),
        Metric("graylog_decoded", 3076174718),
        Result(state=State.OK, summary="Last updated: 2025-05-09 14:25:49"),
    ]
