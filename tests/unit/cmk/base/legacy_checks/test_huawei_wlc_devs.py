#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.huawei_wlc_devs import (
    check_huawei_wlc_devs_cpu,
    check_huawei_wlc_devs_mem,
    discovery_huawei_wlc_devs_cpu,
    discovery_huawei_wlc_devs_mem,
    parse_huawei_wlc_devs,
)


def parsed() -> Mapping[str, Any]:
    """Parsed WLC device data for testing."""
    string_table = [
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
    return parse_huawei_wlc_devs(string_table)


def test_huawei_wlc_devs_discovery_mem():
    """Test huawei_wlc_devs memory discovery."""
    services = list(discovery_huawei_wlc_devs_mem(parsed()))

    assert len(services) == 1
    assert services == [("AC6508", {})]


def test_huawei_wlc_devs_discovery_cpu():
    """Test huawei_wlc_devs CPU discovery."""
    services = list(discovery_huawei_wlc_devs_cpu(parsed()))

    assert len(services) == 1
    assert services == [("AC6508", {})]


def test_huawei_wlc_devs_check_mem():
    """Test huawei_wlc_devs memory check."""
    params = {"levels": (80.0, 90.0)}
    result = list(check_huawei_wlc_devs_mem("AC6508", params, parsed()))

    assert len(result) == 1
    state, message, metrics = result[0]
    assert state == 0
    assert "Used: 28.00%" in message
    assert ("mem_used_percent", 28.0, 80.0, 90.0) in metrics


def test_huawei_wlc_devs_check_cpu():
    """Test huawei_wlc_devs CPU check."""
    params = {"levels": (80.0, 90.0)}
    result = list(check_huawei_wlc_devs_cpu("AC6508", params, parsed()))

    assert len(result) == 1
    state, message, metrics = result[0]
    assert state == 0
    assert "Usage: 4.00%" in message
    assert ("cpu_percent", 4.0, 80.0, 90.0) in metrics


def test_huawei_wlc_devs_check_missing_item():
    """Test huawei_wlc_devs check with missing item."""
    params = {"levels": (80.0, 90.0)}
    result = list(check_huawei_wlc_devs_mem("NonExistent", params, parsed()))

    assert len(result) == 0
