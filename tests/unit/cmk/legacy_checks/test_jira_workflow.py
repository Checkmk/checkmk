#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.jira_workflow import (
    check_jira_workflow,
    discover_jira_workflow,
    parse_jira_workflow,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"my_project1":',
                    '{"in',
                    'progress":',
                    "16,",
                    '"waiting":',
                    "56,",
                    '"need',
                    'help":',
                    "42}}",
                ]
            ],
            [
                Service(item="My_Project1/In Progress"),
                Service(item="My_Project1/Need Help"),
                Service(item="My_Project1/Waiting"),
            ],
        ),
    ],
)
def test_discover_jira_workflow(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for jira_workflow check."""
    parsed = parse_jira_workflow(string_table)
    result = sorted(list(discover_jira_workflow(parsed)), key=lambda s: s.item or "")
    expected = sorted(expected_discoveries, key=lambda s: s.item or "")
    assert result == expected


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "My_Project1/In Progress",
            {},
            [
                [
                    '{"my_project1":',
                    '{"in',
                    'progress":',
                    "16,",
                    '"waiting":',
                    "56,",
                    '"need',
                    'help":',
                    "42}}",
                ]
            ],
            [
                Result(state=State.OK, summary="Total number of issues: 16"),
                Metric("jira_count", 16),
            ],
        ),
        (
            "My_Project1/Need Help",
            {},
            [
                [
                    '{"my_project1":',
                    '{"in',
                    'progress":',
                    "16,",
                    '"waiting":',
                    "56,",
                    '"need',
                    'help":',
                    "42}}",
                ]
            ],
            [
                Result(state=State.OK, summary="Total number of issues: 42"),
                Metric("jira_count", 42),
            ],
        ),
        (
            "My_Project1/Waiting",
            {},
            [
                [
                    '{"my_project1":',
                    '{"in',
                    'progress":',
                    "16,",
                    '"waiting":',
                    "56,",
                    '"need',
                    'help":',
                    "42}}",
                ]
            ],
            [
                Result(state=State.OK, summary="Total number of issues: 56"),
                Metric("jira_count", 56),
            ],
        ),
    ],
)
def test_check_jira_workflow(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for jira_workflow check."""
    parsed = parse_jira_workflow(string_table)
    result = list(check_jira_workflow(item, params, parsed))
    assert result == expected_results
