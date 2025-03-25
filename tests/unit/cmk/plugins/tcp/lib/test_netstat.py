#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.tcp.lib.models import Connection, ConnectionState, Section, SplitIP
from cmk.plugins.tcp.lib.netstat import check_netstat_generic, split_ip_address

DEFAULT_SECTION = [
    Connection(
        proto="TCP",
        local_address=SplitIP("127.0.0.1", "80"),
        remote_address=SplitIP("192.168.1.111", "5555"),
        state=ConnectionState.LISTENING,
    ),
    Connection(
        proto="TCP",
        local_address=SplitIP("127.0.0.1", "80"),
        remote_address=SplitIP("192.168.1.112", "5556"),
        state=ConnectionState.CLOSING,
    ),
    Connection(
        proto="UDP",
        local_address=SplitIP("127.0.0.1", "8000"),
        remote_address=SplitIP("192.168.1.113", "5557"),
        state=ConnectionState.LISTENING,
    ),
]


@pytest.mark.parametrize(
    ["section", "params", "expected"],
    [
        pytest.param(
            DEFAULT_SECTION,
            {"min_states": ("no_levels", None), "max_states": ("no_levels", None)},
            [Result(state=State.OK, summary="3.00"), Metric("connections", 3.0)],
            id="no parameters",
        ),
        pytest.param(
            DEFAULT_SECTION,
            {
                "local_port": "80",
                "min_states": ("no_levels", None),
                "max_states": ("no_levels", None),
            },
            [Result(state=State.OK, summary="2.00"), Metric(name="connections", value=2)],
            id="local port filter",
        ),
        pytest.param(
            DEFAULT_SECTION,
            {
                "state": "LISTENING",
                "min_states": ("no_levels", None),
                "max_states": ("no_levels", None),
            },
            [Result(state=State.OK, summary="2.00"), Metric(name="connections", value=2)],
            id="state filter",
        ),
        pytest.param(
            DEFAULT_SECTION,
            {"max_states": ("fixed", (1, 5)), "min_states": ("no_levels", None)},
            [
                Result(state=State.WARN, summary="3.00 (warn/crit at 1.00/5.00)"),
                Metric(name="connections", value=3, levels=(1, 5)),
            ],
            id="WARN level exceeded",
        ),
    ],
)
def test_check_netstat_generic(
    section: Section, params: Mapping[str, Any], expected: CheckResult
) -> None:
    assert list(check_netstat_generic(None, params, section)) == expected


@pytest.mark.parametrize(
    ["address_string", "expected"],
    [
        pytest.param("127.0.0.1:80", SplitIP("127.0.0.1", "80")),
        pytest.param("::1:80", SplitIP("::1", "80")),
        pytest.param("::1:80", SplitIP("::1", "80")),
        pytest.param("127.0.0.1.80", SplitIP("127.0.0.1", "80")),
        pytest.param("*:*", SplitIP("*", "*")),
    ],
)
def test_split_ip_address(address_string: str, expected: SplitIP) -> None:
    assert split_ip_address(address_string) == expected
