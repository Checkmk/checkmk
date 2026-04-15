#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.azure_agent_info import (
    check_azure_agent_info,
    DEFAULT_PARAMS,
    discover_azure_agent_info,
    parse_azure_agent_info,
)


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.azure_v2.agent_based.azure_agent_info.get_value_store",
        lambda: {},
    )


STRING_TABLE_WITH_ISSUES: StringTable = [
    ["issue", '{"type": "warning", "issued_by": "component", "msg": "something bad"}'],
    ["issue", '{"type": "exception", "issued_by": "other", "msg": "an error"}'],
]

STRING_TABLE_WITH_BAILOUT: StringTable = [
    ["agent-bailout", '[2, "Agent failed to connect"]'],
]


@pytest.mark.parametrize(
    "string_table, monitored_resources, issues, agent_bailouts",
    [
        pytest.param(
            STRING_TABLE_WITH_ISSUES,
            ["MyVM"],
            {
                "exception": [{"issued_by": "other", "msg": "an error", "type": "exception"}],
                "warning": [{"issued_by": "component", "msg": "something bad", "type": "warning"}],
            },
            [],
            id="with issues",
        ),
        pytest.param(
            STRING_TABLE_WITH_BAILOUT,
            ["MyVM"],
            {},
            [(2, "Agent failed to connect")],
            id="with bailout",
        ),
    ],
)
def test_parse_azure_agent_info(
    string_table: StringTable,
    monitored_resources: list[str],
    issues: dict[str, list[dict[str, str]]],
    agent_bailouts: list[tuple[int, str]],
) -> None:
    result = parse_azure_agent_info(string_table)
    assert result.issues == issues
    assert result.agent_bailouts == agent_bailouts


def test_discover() -> None:
    parsed = parse_azure_agent_info(STRING_TABLE_WITH_BAILOUT)
    result = list(discover_azure_agent_info(parsed))
    assert result == [Service()]


@pytest.mark.usefixtures("empty_value_store")
def test_check_no_issues() -> None:
    parsed = parse_azure_agent_info(STRING_TABLE_WITH_BAILOUT)
    result = list(check_azure_agent_info(DEFAULT_PARAMS, parsed))
    assert result == [
        Result(state=State.CRIT, summary="Agent failed to connect"),
        Result(state=State.OK, summary="Warnings: 0"),
        Result(state=State.OK, summary="Exceptions: 0"),
    ]


@pytest.mark.usefixtures("empty_value_store")
def test_check_bailout() -> None:
    parsed = parse_azure_agent_info(STRING_TABLE_WITH_BAILOUT)
    result = list(check_azure_agent_info(DEFAULT_PARAMS, parsed))
    assert any(
        isinstance(r, Result) and r.state == State.CRIT and "Agent failed to connect" in r.summary
        for r in result
    )


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "string_table, expected_states",
    [
        (
            STRING_TABLE_WITH_ISSUES,
            # 1 warning issue hits exception_levels (1,1) -> CRIT, warning_levels (1,10) -> WARN
            [State.WARN, State.CRIT],
        ),
    ],
)
def test_check_issues(string_table: StringTable, expected_states: list[State]) -> None:
    parsed = parse_azure_agent_info(string_table)
    result = list(check_azure_agent_info(DEFAULT_PARAMS, parsed))
    issue_states = [r.state for r in result if isinstance(r, Result) and r.state != State.OK]
    assert set(expected_states) == set(issue_states)
