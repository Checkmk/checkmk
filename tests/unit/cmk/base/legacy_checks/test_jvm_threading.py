#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks import jolokia_jvm_threading as jvm_threading

from cmk.agent_based.legacy.v0_unstable import LegacyCheckResult

Section = Mapping[str, Any]


def _section() -> Section:
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


def test_discovery() -> None:
    assert list(jvm_threading.discover_jolokia_jvm_threading_pool(_section())) == [
        ("a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10032", {}),
        ("a02a-www-susa001 ThreadPool ajp-nio-127.0.0.1-10031", {}),
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
    ],
)
def test_check(
    item: str,
    params: dict[str, tuple[str, tuple[int, int]]],
    expected_result: LegacyCheckResult,
) -> None:
    assert list(jvm_threading.check_jolokia_jvm_threading_pool(item, params, _section())) == list(
        expected_result
    )
