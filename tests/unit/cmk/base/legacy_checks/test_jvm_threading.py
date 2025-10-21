#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any
from unittest.mock import patch

import pytest

from cmk.agent_based.legacy.v0_unstable import LegacyCheckResult
from cmk.base.legacy_checks import jolokia_jvm_threading as jvm_threading

Section = Mapping[str, Any]


def _section_pool() -> Section:
    """Pool-specific test data from regression test"""
    return jvm_threading.parse_jolokia_jvm_threading(
        [
            [
                "a02a-www-susa001",
                "*:name=*,type=ThreadPool/maxThreads,currentThreadCount,currentThreadsBusy/",
                """{"susa-service:name=\\"ajp-nio-127.0.0.1-10032\\",type=ThreadPool": {"currentThreadsBusy": 1,
                "currentThreadCount": 25, "maxThreads": -1}, "susa-service:name=\\"ajp-nio-127.0.0.1-10031\\",type=ThreadPool":
                {"currentThreadsBusy": 27, "currentThreadCount": 28, "maxThreads": 30}}""",
            ]
        ]
    )


def _section_main() -> Section:
    """Main check test data from regression test"""
    return jvm_threading.parse_jolokia_jvm_threading(
        [
            [
                "JIRA",
                "*:name=*,type=ThreadPool/maxThreads,currentThreadCount,currentThreadsBusy/",
                '{"Catalina:name=\\"http-nio-8080\\",type=ThreadPool": {"maxThreads": 150,'
                ' "currentThreadCount": 25, "currentThreadsBusy": 12}}',
            ],
            [
                "JIRA",
                "java.lang:type=Threading",
                '{"PeakThreadCount": 142, "ThreadCpuTimeEnabled": true, "ObjectName": {"objectName": "java.lang:type=Threading"}, "CurrentThreadUserTime": 148790000000, "AllThreadIds": [3510, 3474, 3233, 2323, 2322, 2321, 234, 218, 217, 215, 214, 213, 212, 206, 205, 204, 203, 202, 201, 200, 199, 198, 197, 196, 195, 194, 193, 192, 191, 188, 187, 186, 185, 183, 182, 181, 180, 179, 178, 175, 174, 173, 172, 171, 169, 164, 159, 156, 155, 144, 139, 138, 137, 136, 135, 134, 133, 128, 119, 118, 117, 116, 115, 114, 113, 112, 111, 110, 109, 108, 107, 106, 105, 104, 103, 102, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69, 68, 67, 66, 65, 64, 63, 62, 32, 31, 30, 29, 27, 26, 25, 23, 21, 20, 19, 18, 17, 16, 11, 10, 4, 3, 2, 1], "ThreadCpuTimeSupported": true, "ThreadContentionMonitoringEnabled": false, "ThreadCount": 131, "SynchronizerUsageSupported": true, "DaemonThreadCount": 115, "CurrentThreadCpuTimeSupported": true, "ThreadAllocatedMemorySupported": true, "ThreadAllocatedMemoryEnabled": true, "CurrentThreadCpuTime": 152910232714, "TotalStartedThreadCount": 3506, "ThreadContentionMonitoringSupported": true, "ObjectMonitorUsageSupported": true}',
            ],
        ]
    )


# Tests for main jolokia_jvm_threading check


def test_discover_jolokia_jvm_threading() -> None:
    """Test discovery for main check"""
    assert list(jvm_threading.discover_jolokia_jvm_threading(_section_main())) == [
        ("JIRA", {}),
    ]


@patch("cmk.base.legacy_checks.jolokia_jvm_threading.get_value_store")
@patch("cmk.base.legacy_checks.jolokia_jvm_threading.get_rate")
def test_check_jolokia_jvm_threading_basic(mock_get_rate: Any, mock_get_value_store: Any) -> None:
    """Test main check with basic parameters"""
    # Mock the rate calculation to return 0.0 for ThreadRate
    mock_get_rate.return_value = 0.0
    mock_get_value_store.return_value = {}

    result = list(
        jvm_threading.check_jolokia_jvm_threading(
            "JIRA", {"daemonthreadcount_levels": (90, 100)}, _section_main()
        )
    )

    expected = [
        (0, "Count: 131", [("ThreadCount", 131, None, None)]),
        (0, "Rate: 0.00", [("ThreadRate", 0.0, None, None)]),
        (
            2,
            "Daemon threads: 115 (warn/crit at 90/100)",
            [("DaemonThreadCount", 115, 90, 100)],
        ),
        (0, "Peak count: 142", [("PeakThreadCount", 142, None, None)]),
        (
            0,
            "Total started: 3506",
            [("TotalStartedThreadCount", 3506, None, None)],
        ),
    ]

    assert result == expected


@patch("cmk.base.legacy_checks.jolokia_jvm_threading.get_value_store")
@patch("cmk.base.legacy_checks.jolokia_jvm_threading.get_rate")
def test_check_jolokia_jvm_threading_no_daemon_levels(
    mock_get_rate: Any, mock_get_value_store: Any
) -> None:
    """Test main check without daemon thread levels"""
    mock_get_rate.return_value = 0.0
    mock_get_value_store.return_value = {}

    result = list(jvm_threading.check_jolokia_jvm_threading("JIRA", {}, _section_main()))

    # Should have daemon thread count without levels
    daemon_result = [r for r in result if "Daemon threads" in str(r)]
    assert len(daemon_result) == 1
    assert daemon_result[0][0] == 0  # No warning/critical status
    assert "115" in daemon_result[0][1]  # Contains the count


# Tests for jolokia_jvm_threading_pool check


def test_discover_jolokia_jvm_threading_pool() -> None:
    """Test discovery for pool check"""
    assert list(jvm_threading.discover_jolokia_jvm_threading_pool(_section_pool())) == [
        ("a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10032", {}),
        ("a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031", {}),
    ]


def test_discover_jolokia_jvm_threading_pool_with_main_data() -> None:
    """Test pool discovery with data from main check regression test"""
    assert list(jvm_threading.discover_jolokia_jvm_threading_pool(_section_main())) == [
        ("JIRA ThreadPool http-nio-8080", {}),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10032",
            {
                "currentThreadsBusy": ("percentage", (80, 90)),
            },
            [(0, "Maximum threads: not set (unlimited)")],
            id="No maxThreads",
        ),
        pytest.param(
            "a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031",
            {
                "currentThreadsBusy": ("percentage", (80, 90)),
            },
            [
                (0, "Maximum threads: 30"),
                (
                    2,
                    "Busy: 27 (warn/crit at 24/27)",
                    [("currentThreadsBusy", 27, 24.0, 27.0, None, 30)],
                ),
                (0, "Total: 28", [("currentThreadCount", 28, None, None, None, 30)]),
            ],
            id="CRIT on currentThreadsBusy - percentage",
        ),
        pytest.param(
            "a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031",
            {
                "currentThreadCount": ("absolute", (25, 29)),
            },
            [
                (0, "Maximum threads: 30"),
                (
                    0,
                    "Busy: 27",
                    [("currentThreadsBusy", 27, None, None, None, 30)],
                ),
                (
                    1,
                    "Total: 28 (warn/crit at 25/29)",
                    [("currentThreadCount", 28, 25, 29, None, 30)],
                ),
            ],
            id="WARN on currentThreadCount - absolute",
        ),
        pytest.param(
            "JIRA ThreadPool http-nio-8080",
            {
                "currentThreadsBusy": ("absolute", (8, 135)),
            },
            [
                (0, "Maximum threads: 150"),
                (
                    1,
                    "Busy: 12 (warn/crit at 8/135)",
                    [("currentThreadsBusy", 12, 8, 135, None, 150)],
                ),
                (0, "Total: 25", [("currentThreadCount", 25, None, None, None, 150)]),
            ],
            id="Main data - WARN on currentThreadsBusy absolute",
        ),
    ],
)
def test_check(
    item: str,
    params: dict[str, tuple[str, tuple[int, int]]],
    expected_result: LegacyCheckResult,
) -> None:
    """Test pool check with various parameters"""
    section = _section_main() if "JIRA" in item else _section_pool()
    assert list(jvm_threading.check_jolokia_jvm_threading_pool(item, params, section)) == list(
        expected_result
    )
