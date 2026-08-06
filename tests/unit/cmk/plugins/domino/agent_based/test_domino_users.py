#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.domino.agent_based import domino_users
from cmk.plugins.domino.agent_based.domino_users import DominoUsersParams

# .1.3.6.1.4.1.334.72.1.1.6.3.6 -- lnServerUsers
STRING_TABLE: StringTable = [["500"]]

PARAMS = DominoUsersParams(levels=("fixed", (1000, 1500)))


def test_parse_keeps_the_string_table() -> None:
    assert domino_users.parse_domino_users(STRING_TABLE) == STRING_TABLE


def test_discover_when_the_server_answers() -> None:
    assert list(domino_users.discover_domino_users(STRING_TABLE)) == [Service()]


def test_discover_without_any_output() -> None:
    assert list(domino_users.discover_domino_users([])) == []


@pytest.mark.parametrize(
    "users,expected_result",
    [
        pytest.param(
            "500",
            Result(state=State.OK, summary="Domino users on server: 500"),
            id="below_the_levels",
        ),
        pytest.param(
            "1000",
            Result(
                state=State.WARN,
                summary="Domino users on server: 1000 (warn/crit at 1000/1500)",
            ),
            id="at_the_warn_level",
        ),
        pytest.param(
            "1500",
            Result(
                state=State.CRIT,
                summary="Domino users on server: 1500 (warn/crit at 1000/1500)",
            ),
            id="at_the_crit_level",
        ),
        pytest.param(
            "2000",
            Result(
                state=State.CRIT,
                summary="Domino users on server: 2000 (warn/crit at 1000/1500)",
            ),
            id="above_the_crit_level",
        ),
    ],
)
def test_check_applies_the_upper_levels(users: str, expected_result: Result) -> None:
    section: StringTable = [[users]]

    assert list(domino_users.check_domino_users(PARAMS, section)) == [
        expected_result,
        Metric("users", float(users), levels=(1000.0, 1500.0)),
    ]


def test_check_without_any_output_stays_silent() -> None:
    assert list(domino_users.check_domino_users(PARAMS, [])) == []
