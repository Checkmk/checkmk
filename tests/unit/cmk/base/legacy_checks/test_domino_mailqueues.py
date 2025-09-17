#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.domino_mailqueues import (
    check_domino_mailqueues,
    discover_domino_mailqueues,
    parse_domino_mailqueues,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["1", "4711", "815", "1", "12"]],
            [
                ("lnDeadMail", {}),
                ("lnWaitingMail", {}),
                ("lnMailHold", {}),
                ("lnMailTotalPending", {}),
                ("InMailWaitingforDNS", {}),
            ],
        ),
    ],
)
def test_discover_domino_mailqueues(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for domino_mailqueues check."""
    parsed = parse_domino_mailqueues(string_table)
    result = list(discover_domino_mailqueues(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "lnDeadMail",
            {"queue_length": (300, 350)},
            [["1", "4711", "815", "1", "12"]],
            [(0, "Dead mails: 1", [("mails", 1, 300, 350)])],
        ),
        (
            "lnWaitingMail",
            {"queue_length": (300, 350)},
            [["1", "4711", "815", "1", "12"]],
            [(2, "Waiting mails: 4711 (warn/crit at 300/350)", [("mails", 4711, 300, 350)])],
        ),
        (
            "lnMailHold",
            {"queue_length": (300, 350)},
            [["1", "4711", "815", "1", "12"]],
            [(2, "Mails on hold: 815 (warn/crit at 300/350)", [("mails", 815, 300, 350)])],
        ),
        (
            "lnMailTotalPending",
            {"queue_length": (300, 350)},
            [["1", "4711", "815", "1", "12"]],
            [(0, "Total pending mails: 1", [("mails", 1, 300, 350)])],
        ),
        (
            "InMailWaitingforDNS",
            {"queue_length": (300, 350)},
            [["1", "4711", "815", "1", "12"]],
            [(0, "Mails waiting for DNS: 12", [("mails", 12, 300, 350)])],
        ),
    ],
)
def test_check_domino_mailqueues(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for domino_mailqueues check."""
    parsed = parse_domino_mailqueues(string_table)
    result = list(check_domino_mailqueues(item, params, parsed))
    assert result == expected_results
