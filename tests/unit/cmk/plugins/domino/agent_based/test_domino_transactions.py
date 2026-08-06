#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.domino.agent_based import domino_transactions
from cmk.plugins.domino.agent_based.domino_transactions import DominoTransactionsParams

# .1.3.6.1.4.1.334.72.1.1.6.3.2 -- lnServerTransPerMinute
STRING_TABLE: StringTable = [["12345"]]

PARAMS = DominoTransactionsParams(levels=(30000, 35000))


def test_parse_keeps_the_string_table() -> None:
    assert domino_transactions.parse_domino_transactions(STRING_TABLE) == STRING_TABLE


def test_discover_when_the_server_answers() -> None:
    assert list(domino_transactions.discover_domino_transactions(STRING_TABLE)) == [Service()]


def test_discover_without_any_output() -> None:
    assert list(domino_transactions.discover_domino_transactions([])) == []


@pytest.mark.parametrize(
    "transactions,expected_result",
    [
        pytest.param(
            "12345",
            Result(state=State.OK, summary="Transactions per minute (avg): 12345"),
            id="below_the_levels",
        ),
        pytest.param(
            "30000",
            Result(
                state=State.WARN,
                summary="Transactions per minute (avg): 30000 (warn/crit at 30000/35000)",
            ),
            id="at_the_warn_level",
        ),
        pytest.param(
            "35000",
            Result(
                state=State.CRIT,
                summary="Transactions per minute (avg): 35000 (warn/crit at 30000/35000)",
            ),
            id="at_the_crit_level",
        ),
        pytest.param(
            "40000",
            Result(
                state=State.CRIT,
                summary="Transactions per minute (avg): 40000 (warn/crit at 30000/35000)",
            ),
            id="above_the_crit_level",
        ),
    ],
)
def test_check_applies_the_upper_levels(transactions: str, expected_result: Result) -> None:
    section: StringTable = [[transactions]]

    assert list(domino_transactions.check_domino_transactions(PARAMS, section)) == [
        expected_result,
        Metric("transactions", float(transactions), levels=(30000.0, 35000.0)),
    ]


def test_check_without_any_output_stays_silent() -> None:
    assert list(domino_transactions.check_domino_transactions(PARAMS, [])) == []
