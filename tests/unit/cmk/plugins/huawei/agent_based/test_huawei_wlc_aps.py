#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.huawei.agent_based.huawei_wlc_aps import (
    check_huawei_wlc_aps_cpu,
    check_huawei_wlc_aps_mem,
    check_huawei_wlc_aps_status,
    check_huawei_wlc_aps_temp,
    discovery_huawei_wlc_aps_cpu,
    discovery_huawei_wlc_aps_mem,
    discovery_huawei_wlc_aps_status,
    discovery_huawei_wlc_aps_temp,
    HuaweiWlcApsLevelsParams,
    parse_huawei_wlc_aps,
)

STRING_TABLE = [
    [
        ["8", "23", "66", "40", "1"],
        ["4", "0", "0", "255", "0"],
        ["8", "23", "1", "43", "0"],
        ["8", "23", "1", "38", "0"],
        ["8", "23", "1", "38", "0"],
        ["8", "23", "1", "39", "1"],
        ["8", "23", "1", "37", "1"],
        ["8", "23", "1", "38", "0"],
    ],
    [
        ["to-ap-04", "1", "12", "1"],
        ["to-ap-04", "1", "1", "0"],
        ["to-simu", "", "87", "55"],
        ["to-simu", "", "93", "34"],
        ["huawei-test-ap-01", "1", "10", "0"],
        ["huawei-test-ap-01", "1", "7", "0"],
        ["to-ap-02", "1", "13", "0"],
        ["to-ap-02", "1", "1", "0"],
        ["to-ap-06", "1", "89", "0"],
        ["to-ap-06", "1", "1", "0"],
        ["to-ap-03", "1", "13", "2"],
        ["to-ap-03", "1", "1", "0"],
        ["to-ap-05", "1", "13", "0"],
        ["to-ap-05", "1", "1", "0"],
        ["to-ap-01", "1", "12", "0"],
        ["to-ap-01", "1", "1", "0"],
    ],
]

PARSED = parse_huawei_wlc_aps(STRING_TABLE)

EXPECTED_APS = sorted(
    [
        "huawei-test-ap-01",
        "to-ap-01",
        "to-ap-02",
        "to-ap-03",
        "to-ap-04",
        "to-ap-05",
        "to-ap-06",
        "to-simu",
    ]
)


def test_parse_huawei_wlc_aps_handles_missing_radio_rows() -> None:
    string_table = [
        [
            ["8", "23", "66", "40", "1"],
            ["8", "23", "66", "40", "1"],
        ],
        [
            ["to-ap-01", "1", "12", "1"],
            ["to-ap-01", "1", "1", "0"],
            ["to-ap-02", "1", "13", "0"],
        ],
    ]
    parsed = parse_huawei_wlc_aps(string_table)
    assert "to-ap-01" in parsed
    assert "to-ap-02" not in parsed


def test_huawei_wlc_aps_discovery_status() -> None:
    services = sorted(s.item or "" for s in discovery_huawei_wlc_aps_status(PARSED))
    assert services == EXPECTED_APS


def test_huawei_wlc_aps_discovery_cpu() -> None:
    services = sorted(s.item or "" for s in discovery_huawei_wlc_aps_cpu(PARSED))
    assert services == EXPECTED_APS


def test_huawei_wlc_aps_discovery_mem() -> None:
    services = sorted(s.item or "" for s in discovery_huawei_wlc_aps_mem(PARSED))
    assert services == EXPECTED_APS


def test_huawei_wlc_aps_discovery_temp() -> None:
    services = sorted(s.item or "" for s in discovery_huawei_wlc_aps_temp(PARSED))
    assert services == EXPECTED_APS


def test_huawei_wlc_aps_check_status() -> None:
    params: HuaweiWlcApsLevelsParams = {"levels": (80.0, 90.0)}
    results = list(check_huawei_wlc_aps_status("huawei-test-ap-01", params, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    # AP status, connected users, 2.4GHz users, 2.4GHz radio, 2.4GHz ch usage,
    # 5GHz users, 5GHz radio, 5GHz ch usage = 8 Result objects
    assert len(result_objs) == 8
    assert result_objs[0].state == State.OK
    assert result_objs[0].summary == "Normal"
    assert "Connected users: 0" in result_objs[1].summary


def test_huawei_wlc_aps_check_cpu() -> None:
    params: HuaweiWlcApsLevelsParams = {"levels": (80.0, 90.0)}
    results = list(check_huawei_wlc_aps_cpu("huawei-test-ap-01", params, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == State.OK
    assert "Usage" in result_objs[0].summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == "cpu_percent"


def test_huawei_wlc_aps_check_mem() -> None:
    params: HuaweiWlcApsLevelsParams = {"levels": (80.0, 90.0)}
    results = list(check_huawei_wlc_aps_mem("huawei-test-ap-01", params, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == State.OK
    assert "Used" in result_objs[0].summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == "mem_used_percent"


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.huawei.agent_based.huawei_wlc_aps.get_value_store",
        lambda: {},
    )


def test_huawei_wlc_aps_check_temp(empty_value_store: None) -> None:
    results = list(check_huawei_wlc_aps_temp("huawei-test-ap-01", {"levels": (70.0, 75.0)}, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    assert len(result_objs) >= 1
    assert result_objs[0].state == State.OK
    assert "43" in result_objs[0].summary


def test_huawei_wlc_aps_check_temp_invalid(empty_value_store: None) -> None:
    results = list(check_huawei_wlc_aps_temp("to-simu", {"levels": (70.0, 75.0)}, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    assert len(result_objs) == 1
    assert result_objs[0].state == State.OK
    assert result_objs[0].summary == "invalid"
