#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.domino.agent_based.domino_mailqueues import (
    check_domino_mailqueues,
    discover_domino_mailqueues,
    DominoMailqueuesParams,
    parse_domino_mailqueues,
)

# lnDeadMail, lnWaitingMail, lnMailHold, lnMailTotalPending, InMailWaitingforDNS
STRING_TABLE: StringTable = [["1", "4711", "815", "1", "12"]]

PARAMS = DominoMailqueuesParams(queue_length=(300, 350))


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            STRING_TABLE,
            [
                "lnDeadMail",
                "lnWaitingMail",
                "lnMailHold",
                "lnMailTotalPending",
                "InMailWaitingforDNS",
            ],
        ),
    ],
)
def test_discover_domino_mailqueues(
    string_table: StringTable, expected_discoveries: Sequence[str]
) -> None:
    parsed = parse_domino_mailqueues(string_table)
    result = sorted(s.item or "" for s in discover_domino_mailqueues(parsed))
    assert result == sorted(expected_discoveries)


def test_parse_pairs_each_oid_with_its_label() -> None:
    assert parse_domino_mailqueues(STRING_TABLE) == {
        "lnDeadMail": ("Dead mails", 1),
        "lnWaitingMail": ("Waiting mails", 4711),
        "lnMailHold": ("Mails on hold", 815),
        "lnMailTotalPending": ("Total pending mails", 1),
        "InMailWaitingforDNS": ("Mails waiting for DNS", 12),
    }


@pytest.mark.parametrize(
    "item, expected_result, expected_value",
    [
        pytest.param(
            "lnDeadMail",
            Result(state=State.OK, summary="Dead mails: 1"),
            1.0,
            id="dead_below_the_levels",
        ),
        pytest.param(
            "lnWaitingMail",
            Result(state=State.CRIT, summary="Waiting mails: 4711 (warn/crit at 300/350)"),
            4711.0,
            id="waiting_above_the_crit_level",
        ),
        pytest.param(
            "lnMailHold",
            Result(state=State.CRIT, summary="Mails on hold: 815 (warn/crit at 300/350)"),
            815.0,
            id="hold_above_the_crit_level",
        ),
        pytest.param(
            "lnMailTotalPending",
            Result(state=State.OK, summary="Total pending mails: 1"),
            1.0,
            id="pending_below_the_levels",
        ),
        pytest.param(
            "InMailWaitingforDNS",
            Result(state=State.OK, summary="Mails waiting for DNS: 12"),
            12.0,
            id="waiting_for_dns_below_the_levels",
        ),
    ],
)
def test_check_domino_mailqueues(item: str, expected_result: Result, expected_value: float) -> None:
    parsed = parse_domino_mailqueues(STRING_TABLE)

    assert list(check_domino_mailqueues(item, PARAMS, parsed)) == [
        expected_result,
        Metric("mails", expected_value, levels=(300.0, 350.0)),
    ]


def test_check_without_configured_levels() -> None:
    """queue_length is optional, and the check must then report the count without levels."""
    parsed = parse_domino_mailqueues(STRING_TABLE)

    assert list(check_domino_mailqueues("lnWaitingMail", DominoMailqueuesParams(), parsed)) == [
        Result(state=State.OK, summary="Waiting mails: 4711"),
        Metric("mails", 4711.0),
    ]


def test_check_of_a_queue_the_server_no_longer_reports() -> None:
    assert list(check_domino_mailqueues("lnDeadMail", PARAMS, {})) == []
