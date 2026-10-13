#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from unittest.mock import MagicMock, patch

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.jolokia.agent_based import jolokia_jvm_threading as jvm_threading

Section = Mapping[str, object]


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
                (
                    '{"Catalina:name=\\"http-nio-8080\\",type=ThreadPool": {"maxThreads": 150,'
                    ' "currentThreadCount": 25, "currentThreadsBusy": 12}}'
                ),
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
        Service(item="JIRA"),
    ]


@patch("cmk.plugins.jolokia.agent_based.jolokia_jvm_threading.get_value_store")
@patch("cmk.plugins.jolokia.agent_based.jolokia_jvm_threading.get_rate")
def test_check_jolokia_jvm_threading_basic(  # type: ignore[misc]
    mock_get_rate: MagicMock, mock_get_value_store: MagicMock
) -> None:
    """Test main check with basic parameters"""
    # Mock the rate calculation to return 0.0 for ThreadRate
    mock_get_rate.return_value = 0.0
    mock_get_value_store.return_value = {}

    result = list(
        jvm_threading.check_jolokia_jvm_threading(
            "JIRA", {"daemonthreadcount_levels": (90, 100)}, _section_main()
        )
    )

    assert result == [
        Result(state=State.OK, summary="Count: 131"),
        Metric("ThreadCount", 131.0),
        Result(state=State.OK, summary="Rate: 0.00"),
        Metric("ThreadRate", 0.0),
        Result(state=State.CRIT, summary="Daemon threads: 115 (warn/crit at 90/100)"),
        Metric("DaemonThreadCount", 115.0, levels=(90.0, 100.0)),
        Result(state=State.OK, summary="Peak count: 142"),
        Metric("PeakThreadCount", 142.0),
        Result(state=State.OK, summary="Total started: 3506"),
        Metric("TotalStartedThreadCount", 3506.0),
    ]


@patch("cmk.plugins.jolokia.agent_based.jolokia_jvm_threading.get_value_store")
@patch("cmk.plugins.jolokia.agent_based.jolokia_jvm_threading.get_rate")
def test_check_jolokia_jvm_threading_no_daemon_levels(  # type: ignore[misc]
    mock_get_rate: MagicMock, mock_get_value_store: MagicMock
) -> None:
    """Test main check without daemon thread levels"""
    mock_get_rate.return_value = 0.0
    mock_get_value_store.return_value = {}

    result = list(jvm_threading.check_jolokia_jvm_threading("JIRA", {}, _section_main()))

    # Should have daemon thread count without levels
    daemon_result = [r for r in result if isinstance(r, Result) and "Daemon threads" in r.summary]
    assert daemon_result == [Result(state=State.OK, summary="Daemon threads: 115")]


# Tests for jolokia_jvm_threading_pool check


def test_discover_jolokia_jvm_threading_pool() -> None:
    """Test discovery for pool check"""
    assert list(jvm_threading.discover_jolokia_jvm_threading_pool(_section_pool())) == [
        Service(item="a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10032"),
        Service(item="a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031"),
    ]


def test_discover_jolokia_jvm_threading_pool_with_main_data() -> None:
    """Test pool discovery with data from main check regression test"""
    assert list(jvm_threading.discover_jolokia_jvm_threading_pool(_section_main())) == [
        Service(item="JIRA ThreadPool http-nio-8080"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10032",
            {
                "currentThreadsBusy": ("percentage", (80, 90)),
            },
            [Result(state=State.OK, summary="Maximum threads: not set (unlimited)")],
            id="No maxThreads",
        ),
        pytest.param(
            "a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031",
            {
                "currentThreadsBusy": ("percentage", (80, 90)),
            },
            [
                Result(state=State.OK, summary="Maximum threads: 30"),
                Result(state=State.CRIT, summary="Busy: 27 (warn/crit at 24/27)"),
                Metric("currentThreadsBusy", 27.0, levels=(24.0, 27.0), boundaries=(None, 30.0)),
                Result(state=State.OK, summary="Total: 28"),
                Metric("currentThreadCount", 28.0, boundaries=(None, 30.0)),
            ],
            id="CRIT on currentThreadsBusy - percentage",
        ),
        pytest.param(
            "a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031",
            {
                "currentThreadCount": ("absolute", (25, 29)),
            },
            [
                Result(state=State.OK, summary="Maximum threads: 30"),
                Result(state=State.OK, summary="Busy: 27"),
                Metric("currentThreadsBusy", 27.0, boundaries=(None, 30.0)),
                Result(state=State.WARN, summary="Total: 28 (warn/crit at 25/29)"),
                Metric("currentThreadCount", 28.0, levels=(25.0, 29.0), boundaries=(None, 30.0)),
            ],
            id="WARN on currentThreadCount - absolute",
        ),
        pytest.param(
            "JIRA ThreadPool http-nio-8080",
            {
                "currentThreadsBusy": ("absolute", (8, 135)),
            },
            [
                Result(state=State.OK, summary="Maximum threads: 150"),
                Result(state=State.WARN, summary="Busy: 12 (warn/crit at 8/135)"),
                Metric("currentThreadsBusy", 12.0, levels=(8.0, 135.0), boundaries=(None, 150.0)),
                Result(state=State.OK, summary="Total: 25"),
                Metric("currentThreadCount", 25.0, boundaries=(None, 150.0)),
            ],
            id="Main data - WARN on currentThreadsBusy absolute",
        ),
    ],
)
def test_check(
    item: str,
    params: dict[str, tuple[str, tuple[int, int]]],
    expected_result: Sequence[object],
) -> None:
    """Test pool check with various parameters"""
    section = _section_main() if "JIRA" in item else _section_pool()
    assert list(jvm_threading.check_jolokia_jvm_threading_pool(item, params, section)) == list(
        expected_result
    )
