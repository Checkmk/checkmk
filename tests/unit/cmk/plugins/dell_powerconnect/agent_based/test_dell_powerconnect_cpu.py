#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.dell_powerconnect.agent_based.dell_powerconnect_cpu import (
    check_dell_powerconnect_cpu,
    discover_dell_powerconnect_cpu,
    Section,
    snmp_section_dell_powerconnect_cpu,
)

WALK = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.674.10895
.1.3.6.1.4.1.89.1.6 1
.1.3.6.1.4.1.89.1.7 91
.1.3.6.1.4.1.89.1.8 10
.1.3.6.1.4.1.89.1.9 4
"""


def test_cpu_parse(
    as_path: Callable[[str], Path],
) -> None:
    snmp_walk = as_path(WALK)

    assert snmp_is_detected(snmp_section_dell_powerconnect_cpu, snmp_walk)

    assert get_parsed_snmp_section(snmp_section_dell_powerconnect_cpu, snmp_walk) == Section(
        True, 91, 10, 4
    )


def test_cpu_discover() -> None:
    assert (list(discover_dell_powerconnect_cpu(Section(True, 91, 10, 4)))) == [
        Service(),
    ]


@pytest.mark.parametrize(
    "section, result",
    [
        (
            Section(True, 91, 10, 4),
            [
                Result(
                    state=State.CRIT, summary="CPU utilization: 91.00% (warn/crit at 80.00%/90.00%)"
                ),
                Metric("util", 91.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("util1", 10.0, boundaries=(0.0, 100.0)),
                Metric("util5", 4.0, boundaries=(0.0, 100.0)),
            ],
        ),
        (
            Section(False, 91, 10, 4),
            [],
        ),
        (
            Section(True, -10, 10, 4),
            [],
        ),
        (
            Section(True, 999, 10, 4),
            [],
        ),
    ],
)
def test_cpu_check(section: Section, result: CheckResult) -> None:
    assert (
        list(
            check_dell_powerconnect_cpu(
                params={"levels": (80.0, 90.0)},
                section=section,
            )
        )
        == result
    )


def test_cpu_check_ignore(as_path: Callable[[str], Path]) -> None:
    snmp_walk = as_path("""
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.674.10895
.1.3.6.1.4.1.89.1.6 1
.1.3.6.1.4.1.89.1.7
.1.3.6.1.4.1.89.1.8
.1.3.6.1.4.1.89.1.9
    """)

    assert snmp_is_detected(snmp_section_dell_powerconnect_cpu, snmp_walk)

    assert get_parsed_snmp_section(snmp_section_dell_powerconnect_cpu, snmp_walk) is None
