#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.legacy_checks.huawei_wlc_devs import (
    check_huawei_wlc_devs_cpu,
    check_huawei_wlc_devs_mem,
    discovery_huawei_wlc_devs_cpu,
    discovery_huawei_wlc_devs_mem,
    HuaweiWlcDevsLevelsParams,
    parse_huawei_wlc_devs,
)

STRING_TABLE = [
    ["", "0", "0"],
    ["", "0", "0"],
    ["AC6508", "4", "28"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
    ["", "0", "0"],
]

PARSED = parse_huawei_wlc_devs(STRING_TABLE)


def test_huawei_wlc_devs_discovery_mem() -> None:
    services = list(discovery_huawei_wlc_devs_mem(PARSED))
    assert len(services) == 1
    assert services[0].item == "AC6508"


def test_huawei_wlc_devs_discovery_cpu() -> None:
    services = list(discovery_huawei_wlc_devs_cpu(PARSED))
    assert len(services) == 1
    assert services[0].item == "AC6508"


def test_huawei_wlc_devs_check_mem() -> None:
    params: HuaweiWlcDevsLevelsParams = {"levels": (80.0, 90.0)}
    results = list(check_huawei_wlc_devs_mem("AC6508", params, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == State.OK
    assert "Used" in result_objs[0].summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == "mem_used_percent"


def test_huawei_wlc_devs_check_cpu() -> None:
    params: HuaweiWlcDevsLevelsParams = {"levels": (80.0, 90.0)}
    results = list(check_huawei_wlc_devs_cpu("AC6508", params, PARSED))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == State.OK
    assert "Usage" in result_objs[0].summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == "cpu_percent"


def test_huawei_wlc_devs_check_missing_item() -> None:
    params: HuaweiWlcDevsLevelsParams = {"levels": (80.0, 90.0)}
    results = list(check_huawei_wlc_devs_mem("NonExistent", params, PARSED))
    assert len(results) == 0
