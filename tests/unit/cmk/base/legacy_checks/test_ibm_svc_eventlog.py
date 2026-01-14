#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.ibm_svc_eventlog import (
    check_ibm_svc_eventlog,
    discover_ibm_svc_eventlog,
    parse_ibm_svc_eventlog,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "164",
                    "220522214408",
                    "enclosure",
                    "1",
                    "",
                    "",
                    "alert",
                    "no",
                    "085044",
                    "1114",
                    "Enclosure Battery fault type 1",
                    "",
                    "",
                ]
            ],
            [(None, None)],
        ),
    ],
)
def test_discover_ibm_svc_eventlog(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ibm_svc_eventlog check."""
    parsed = parse_ibm_svc_eventlog(string_table)
    result = list(discover_ibm_svc_eventlog(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    "164",
                    "220522214408",
                    "enclosure",
                    "1",
                    "",
                    "",
                    "alert",
                    "no",
                    "085044",
                    "1114",
                    "Enclosure Battery fault type 1",
                    "",
                    "",
                ]
            ],
            [
                1,
                "1 messages not expired and not yet fixed found in event log, last was: Enclosure Battery fault type 1",
            ],
        ),
    ],
)
def test_check_ibm_svc_eventlog(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ibm_svc_eventlog check."""
    parsed = parse_ibm_svc_eventlog(string_table)
    result = list(check_ibm_svc_eventlog(item, params, parsed))
    assert result == expected_results
