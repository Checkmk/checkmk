#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.azure_subscription_info import (
    check_azure_subscription_info,
    DEFAULT_PARAMS,
    discover_azure_subscription_info,
    parse_azure_subscription_info,
)

STRING_TABLE = [
    [
        "monitored-groups",
        '["rg-dev-weu", "networkwatcherrg", "hey-there-rg"]',
    ],
    [
        "remaining-reads",
        "26",
    ],
]


STRING_TABLE_NO_GROUPS = [
    [
        "monitored-groups",
        "[]",
    ],
    [
        "remaining-reads",
        "26",
    ],
]


def test_discover_azure_subscription_info() -> None:
    parsed = parse_azure_subscription_info(STRING_TABLE)
    result = list(discover_azure_subscription_info(parsed))
    assert result == [Service()]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            STRING_TABLE,
            [
                Result(state=State.OK, summary="Remaining API reads: 26"),
                Result(
                    state=State.OK,
                    summary="Monitored groups: rg-dev-weu, networkwatcherrg, hey-there-rg",
                ),
            ],
        ),
        (
            STRING_TABLE_NO_GROUPS,
            [
                Result(state=State.OK, summary="Remaining API reads: 26"),
                Result(state=State.OK, summary="No monitored groups found"),
            ],
        ),
    ],
)
def test_check_azure_subscription_info(string_table: StringTable, expected: CheckResult) -> None:
    parsed = parse_azure_subscription_info(string_table)
    result = list(check_azure_subscription_info(DEFAULT_PARAMS, parsed))
    assert result == expected
