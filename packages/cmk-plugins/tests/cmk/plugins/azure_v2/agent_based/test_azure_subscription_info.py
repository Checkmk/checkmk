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
    Params,
    parse_azure_subscription_info,
)

STRING_TABLE = [
    ["monitored-groups", '["rg-dev-weu", "networkwatcherrg", "hey-there-rg"]'],
    ["remaining-reads", "26"],
    ["monitored-resources", '["MyVM"]'],
]


STRING_TABLE_NO_GROUPS = [
    ["monitored-groups", "[]"],
    ["remaining-reads", "26"],
    ["monitored-resources", '["MyVM"]'],
]


def test_discover_azure_subscription_info() -> None:
    parsed = parse_azure_subscription_info(STRING_TABLE)
    result = list(discover_azure_subscription_info(parsed))
    assert result == [Service(parameters={"discovered_resources": ["MyVM"]})]


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


def test_check_resource_pinning_no_pinning() -> None:
    parsed = parse_azure_subscription_info(STRING_TABLE)
    params: Params = {
        **DEFAULT_PARAMS,
        "resource_pinning": "false",
        "discovered_resources": ["MyVM", "bar"],
    }
    result = list(check_azure_subscription_info(params, parsed))
    assert result == [
        Result(state=State.OK, summary="Remaining API reads: 26"),
        Result(
            state=State.OK, summary="Monitored groups: rg-dev-weu, networkwatcherrg, hey-there-rg"
        ),
    ]


def test_check_resource_pinning_missing_resource() -> None:
    parsed = parse_azure_subscription_info(STRING_TABLE)
    params: Params = {
        **DEFAULT_PARAMS,
        "resource_pinning": "true",
        "discovered_resources": ["MyVM", "bar"],
    }
    result = list(check_azure_subscription_info(params, parsed))
    assert result == [
        Result(state=State.OK, summary="Remaining API reads: 26"),
        Result(state=State.OK, notice="Missing resource: 'bar'(!)"),
        Result(state=State.WARN, summary="Missing resources: 1"),
        Result(
            state=State.OK, summary="Monitored groups: rg-dev-weu, networkwatcherrg, hey-there-rg"
        ),
    ]


def test_check_resource_pinning_new_resource() -> None:
    parsed = parse_azure_subscription_info(STRING_TABLE)
    params: Params = {
        **DEFAULT_PARAMS,
        "resource_pinning": "true",
        "discovered_resources": ["bar"],
    }
    result = list(check_azure_subscription_info(params, parsed))
    assert result == [
        Result(state=State.OK, summary="Remaining API reads: 26"),
        Result(state=State.OK, notice="Missing resource: 'bar'(!)"),
        Result(state=State.OK, notice="New resource: 'MyVM'(!)"),
        Result(state=State.WARN, summary="Missing resources: 1, New resources: 1"),
        Result(
            state=State.OK, summary="Monitored groups: rg-dev-weu, networkwatcherrg, hey-there-rg"
        ),
    ]
