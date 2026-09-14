#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.jolokia.agent_based.jolokia_jvm_runtime import (
    check_jolokia_jvm_runtime_uptime,
    discover_jolokia_jvm_runtime,
    parse_jolokia_jvm_runtime,
)

_STRING_TABLE = [
    [
        "MyJIRA",
        "java.lang:type=Runtime/Uptime,Name",
        '{"Uptime": 34502762, "Name": "1020@jira"}',
    ]
]


def test_parse_jolokia_jvm_runtime() -> None:
    assert parse_jolokia_jvm_runtime(_STRING_TABLE) == {
        "MyJIRA": {"Uptime": 34502762, "Name": "1020@jira"}
    }


def test_parse_jolokia_jvm_runtime_empty_data() -> None:
    assert parse_jolokia_jvm_runtime([]) == {}


def test_parse_jolokia_jvm_runtime_multiple_instances() -> None:
    string_table = [
        [
            "JIRA1",
            "java.lang:type=Runtime/Uptime,Name",
            '{"Uptime": 1000000, "Name": "jira1@host"}',
        ],
        [
            "JIRA2",
            "java.lang:type=Runtime/Uptime,Name",
            '{"Uptime": 2000000, "Name": "jira2@host"}',
        ],
    ]
    result = parse_jolokia_jvm_runtime(string_table)
    assert result == {
        "JIRA1": {"Uptime": 1000000, "Name": "jira1@host"},
        "JIRA2": {"Uptime": 2000000, "Name": "jira2@host"},
    }


def test_discover_jolokia_jvm_runtime() -> None:
    result = list(discover_jolokia_jvm_runtime(parse_jolokia_jvm_runtime(_STRING_TABLE)))
    assert result == [Service(item="MyJIRA")]


def test_discover_jolokia_jvm_runtime_empty_section() -> None:
    assert list(discover_jolokia_jvm_runtime({})) == []


@time_machine.travel("2019-10-11 08:32:51")
def test_check_jolokia_jvm_runtime_uptime() -> None:
    result = list(
        check_jolokia_jvm_runtime_uptime("MyJIRA", {}, parse_jolokia_jvm_runtime(_STRING_TABLE))
    )
    assert len(result) == 2
    summary_result, metric = result
    assert isinstance(summary_result, Result)
    assert summary_result.state == State.OK
    assert summary_result.summary.startswith("Up since ")
    assert summary_result.summary.endswith("uptime: 9:35:02")
    assert isinstance(metric, Metric)
    assert metric.name == "uptime"
    assert metric.value == pytest.approx(34502.762)


def test_check_jolokia_jvm_runtime_uptime_missing_item() -> None:
    result = list(
        check_jolokia_jvm_runtime_uptime(
            "nonexistent", {}, parse_jolokia_jvm_runtime(_STRING_TABLE)
        )
    )
    assert result == []


def test_check_jolokia_jvm_runtime_uptime_missing_uptime_data() -> None:
    parsed: Mapping[str, object] = {"MyJIRA": {"Name": "1020@jira"}}
    assert list(check_jolokia_jvm_runtime_uptime("MyJIRA", {}, parsed)) == []
