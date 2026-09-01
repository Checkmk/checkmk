#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.acme.agent_based.acme_sbc_snmp import (
    check_acme_sbc_snmp,
    discover_acme_sbc_snmp,
    ParamsT,
    parse_acme_sbc_snmp,
    Section,
)

SECTION_1 = [[".1.3.6.1.4.1.9148.3.2.1.1.3.0", "100"], [".1.3.6.1.4.1.9148.3.2.1.1.4.0 2", "2"]]
SECTION_2 = [[".1.3.6.1.4.1.9148.3.2.1.1.3.0", "75"], [".1.3.6.1.4.1.9148.3.2.1.1.4.0 2", "6"]]
SECTION_3 = [[".1.3.6.1.4.1.9148.3.2.1.1.3.0", "50"], [".1.3.6.1.4.1.9148.3.2.1.1.4.0 2", "4"]]


@pytest.mark.parametrize(
    "string_table, expected",
    (
        (SECTION_1, Section(score="100", status="2")),
        (SECTION_2, Section(score="75", status="6")),
        (SECTION_3, Section(score="50", status="4")),
    ),
)
def test_parse_acme_sbc_snmp(string_table: StringTable, expected: Section) -> None:
    assert parse_acme_sbc_snmp(string_table) == expected


def test_discover_acme_sbc_snmp() -> None:
    assert list(discover_acme_sbc_snmp(Section(score="0", status="0"))) == [Service()]


@pytest.mark.parametrize(
    "section, expected",
    (
        (
            Section(score="100", status="2"),
            [
                Result(state=State.OK, summary="Health state: active"),
                Result(state=State.OK, summary="Score: 100%"),
                Metric("health_state", 100.0),
            ],
        ),
        (
            Section(score="75", status="6"),
            [
                Result(state=State.WARN, summary="Health state: active (pending)"),
                Result(state=State.OK, summary="Score: 75%"),
                Metric("health_state", 75.0),
            ],
        ),
        (
            Section(score="50", status="4"),
            [
                Result(state=State.CRIT, summary="Health state: out of service"),
                Result(state=State.OK, summary="Score: 50%"),
                Metric("health_state", 50.0),
            ],
        ),
    ),
)
def test_check_acme_sbc_snmp(section: Section, expected: CheckResult) -> None:
    assert list(check_acme_sbc_snmp(ParamsT(lower_levels=("no_levels", None)), section)) == expected
