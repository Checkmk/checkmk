#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.cisco.agent_based.cisco_ucs_faults import (
    check_cisco_ucs_faults,
    discover_cisco_ucs_faults,
)
from cmk.plugins.collection.agent_based.cisco_ucs_fault_section import (
    parse_cisco_ucs_fault,
    Section,
)


def _section() -> Section:
    return parse_cisco_ucs_fault(
        [
            [
                "sys/rack-unit-1/psu-2",
                "1",
                "374",
                "PSU2_STATUS: Power Supply 2 has lost input or input is out of range : Check input to PS or replace PS 2",
                "5",
            ]
        ]
    )


def test_discover_cisco_ucs_faults_empty() -> None:
    assert list(discover_cisco_ucs_faults({})) == [Service()]


def test_discover_cisco_ucs_faults() -> None:
    assert list(discover_cisco_ucs_faults(_section())) == [Service()]


def test_check_cisco_ucs_faults_empty() -> None:
    assert list(check_cisco_ucs_faults({})) == [Result(state=State.OK, summary="No faults")]


def test_check_cisco_ucs_faults() -> None:
    assert list(check_cisco_ucs_faults(_section())) == [
        Result(
            state=State.CRIT,
            summary="Fault: 374 - PSU2_STATUS: Power Supply 2 has lost input or input is out of range : Check input to PS or replace PS 2",
        ),
    ]
