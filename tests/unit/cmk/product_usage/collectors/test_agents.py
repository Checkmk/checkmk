#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest_mock import MockType

import cmk.product_usage.collectors.agents as agents_collector
from cmk.product_usage.schema import AgentsData


@pytest.mark.parametrize(
    ("plugin_output", "expected"),
    [
        pytest.param("Version: 2.4.0p12, OS: linux", "2.4.0p12", id="first part"),
        pytest.param(
            "Version: 2.3.0p30 (expected 2.4.0p15)(!), OS: windows",
            "2.3.0p30",
            id="mismatch and state marker",
        ),
        pytest.param(
            "Unexpected allowed IP ranges (exceeding: 1.2.3.4)(!), Version: 2.4.0p1",
            "2.4.0p1",
            id="not the first part",
        ),
        pytest.param("Version: 2.4.0p15", "2.4.0p15", id="only part"),
        pytest.param("", None, id="pending service"),
        pytest.param("OS: linux", None, id="no version"),
        pytest.param(
            "Agent plug-ins: 3, Local checks: 0 foo Version: 1.0",
            None,
            id="inside another part",
        ),
    ],
)
def test_parse_agent_version(plugin_output: str, expected: str | None) -> None:
    assert agents_collector.parse_agent_version(plugin_output) == expected


@pytest.mark.parametrize(
    ("raw_version", "expected"),
    [
        ("2.4.0p12", "2.4.0"),
        ("2.4.0", "2.4.0"),
        ("2.4.0b3", "2.4.0"),
        ("2.4.0p1-rc2", "2.4.0"),
        ("2.4.0-2025.10.02", "2.4.0"),
        ("2025.10.02", "other"),
        ("garbage", "other"),
    ],
)
def test_release_series(raw_version: str, expected: str) -> None:
    assert agents_collector.release_series(raw_version) == expected


@pytest.mark.parametrize(
    ("os_version", "expected"),
    [
        ("10.0.17763", "10.0"),
        ("7200-05-03-2148", "7200-05"),
        ("24.04", "24.04"),
        ("12", "12"),
        ("14.5.1", "14.5"),
    ],
)
def test_shorten_os_version(os_version: str, expected: str) -> None:
    assert agents_collector.shorten_os_version(os_version) == expected


def test_collect_counts_hosts_per_version_and_os(local_connection: MockType) -> None:
    ubuntu_24 = {"cmk/os_family": "linux", "cmk/os_name": "Ubuntu", "cmk/os_version": "24.04"}
    windows = {
        "cmk/os_family": "windows",
        "cmk/os_name": "Microsoft Windows Server 2019 Standard",
        "cmk/os_version": "10.0.17763",
    }
    local_connection.query.return_value = [
        [ubuntu_24, "Version: 2.4.0p12, OS: linux"],
        [ubuntu_24, "Version: 2.4.0p3, OS: linux"],
        [windows, "Version: 2.3.0p30 (expected 2.4.0p15)(!), OS: windows"],
        [{}, "Version: 2.4.0p15"],
        [{**ubuntu_24, "cmk/os_version": "22.04"}, ""],
        [{"cmk/os_family": "linux"}, "Version: 2025.10.02, OS: linux"],
    ]

    assert agents_collector.collect() == AgentsData(
        by_version={
            "2.4.0": {"linux": 2, "unknown": 1},
            "2.3.0": {"windows": 1},
            "other": {"linux": 1},
            "unknown": {"linux": 1},
        },
        by_os={
            "Ubuntu": {"24.04": 2, "22.04": 1},
            "Microsoft Windows Server 2019 Standard": {"10.0": 1},
            "unknown": {"unknown": 2},
        },
    )


def test_collect_counts_nothing_on_a_site_without_agent_hosts(local_connection: MockType) -> None:
    local_connection.query.return_value = []

    assert agents_collector.collect() == AgentsData(by_version={}, by_os={})


def test_collect_queries_the_checkmk_agent_service(local_connection: MockType) -> None:
    local_connection.query.return_value = []

    agents_collector.collect()

    query = local_connection.query.call_args.args[0]
    assert "Filter: description = Check_MK Agent" in str(query)
    assert query.supports_json_format()
