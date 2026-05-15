#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.quanta_fan import check_quanta_fan, discover_quanta_fan
from cmk.plugins.quanta.lib import DETECT_QUANTA, parse_quanta


@pytest.mark.parametrize(
    "oids_data, expected_result",
    [
        (
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.8072.3.2.10"},
            False,
        ),
        (
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.8072.3.2.10",
                ".1.3.6.1.4.1.7244.1.2.1.1.1.0": "exists",
            },
            True,
        ),
    ],
)
def test_detect_quanta_fan(
    oids_data: dict[str, str | None],
    expected_result: bool,
) -> None:
    assert (
        evaluate_snmp_detection(detect_spec=DETECT_QUANTA, oid_value_getter=oids_data.get)
        is expected_result
    )


_INFO: list[StringTable] = [
    [
        ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
        ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
        ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
        ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
        ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
        ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
        ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
    ]
]


def test_discover_quanta_fan() -> None:
    parsed = parse_quanta(_INFO)
    result = list(discover_quanta_fan(parsed))
    assert result == [
        Service(item="Fan_SYS0_1"),
        Service(item="Fan_SYS0_2"),
        Service(item="Fan_SYS1_2"),
        Service(item="Fan_SYS2_1"),
        Service(item="Fan_SYS2_2"),
        Service(item="Fan_SYS3_1"),
        Service(item="Fan_SYS3_2"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "Fan_SYS0_1",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.WARN,
                    summary="Speed: 1000 RPM (warn/crit at 800 RPM/1500 RPM)",
                ),
            ],
        ),
        (
            "Fan_SYS0_2",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.CRIT,
                    summary="Speed: 1400 RPM (warn/crit at 1000 RPM/1200 RPM)",
                ),
            ],
        ),
        (
            "Fan_SYS1_2",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Speed: 9200 RPM"),
            ],
        ),
        (
            "Fan_SYS2_1",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Speed: 11300 RPM"),
            ],
        ),
        (
            "Fan_SYS2_2",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.WARN,
                    summary="Speed: 1400 RPM (warn/crit below 2000 RPM/1000 RPM)",
                ),
            ],
        ),
        (
            "Fan_SYS3_1",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.CRIT,
                    summary="Speed: 500 RPM (warn/crit below 2000 RPM/1500 RPM)",
                ),
            ],
        ),
        (
            "Fan_SYS3_2",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Speed: 9300 RPM"),
            ],
        ),
    ],
)
def test_check_quanta_fan(item: str, expected_results: Sequence[object]) -> None:
    parsed = parse_quanta(_INFO)
    result = [r for r in check_quanta_fan(item, {}, parsed) if not isinstance(r, Metric)]
    assert result == expected_results
