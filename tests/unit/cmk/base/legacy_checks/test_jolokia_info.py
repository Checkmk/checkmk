#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.jolokia_info import (
    check_jolokia_info,
    discover_jolokia_info,
    parse_jolokia_info,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "Error:",
                    "mk_jolokia",
                    "requires",
                    "either",
                    "the",
                    "json",
                    "or",
                    "simplejson",
                    "library.",
                    "Please",
                    "either",
                    "use",
                    "a",
                    "Python",
                    "version",
                    "that",
                    "contains",
                    "the",
                    "json",
                    "library",
                    "or",
                    "install",
                    "the",
                    "simplejson",
                    "library",
                    "on",
                    "the",
                    "monitored",
                    "system.",
                ],
                ["INSTANCE1", "ERROR", "HTTP404 No response from server or whatever"],
                ["INSTANCE2", "tomcat", "3.141592", "42.23"],
            ],
            [("Error:", {}), ("INSTANCE1", {}), ("INSTANCE2", {})],
        ),
    ],
)
def test_discover_jolokia_info(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for jolokia_info check."""
    parsed = parse_jolokia_info(string_table)
    result = list(discover_jolokia_info(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Error:",
            {},
            [
                [
                    "Error:",
                    "mk_jolokia",
                    "requires",
                    "either",
                    "the",
                    "json",
                    "or",
                    "simplejson",
                    "library.",
                    "Please",
                    "either",
                    "use",
                    "a",
                    "Python",
                    "version",
                    "that",
                    "contains",
                    "the",
                    "json",
                    "library",
                    "or",
                    "install",
                    "the",
                    "simplejson",
                    "library",
                    "on",
                    "the",
                    "monitored",
                    "system.",
                ],
                ["INSTANCE1", "ERROR", "HTTP404 No response from server or whatever"],
                ["INSTANCE2", "tomcat", "3.141592", "42.23"],
            ],
            [
                (
                    3,
                    "mk_jolokia requires either the json or simplejson library. Please either use a Python version that contains the json library or install the simplejson library on the monitored system.",
                )
            ],
        ),
        (
            "INSTANCE1",
            {},
            [
                [
                    "Error:",
                    "mk_jolokia",
                    "requires",
                    "either",
                    "the",
                    "json",
                    "or",
                    "simplejson",
                    "library.",
                    "Please",
                    "either",
                    "use",
                    "a",
                    "Python",
                    "version",
                    "that",
                    "contains",
                    "the",
                    "json",
                    "library",
                    "or",
                    "install",
                    "the",
                    "simplejson",
                    "library",
                    "on",
                    "the",
                    "monitored",
                    "system.",
                ],
                ["INSTANCE1", "ERROR", "HTTP404 No response from server or whatever"],
                ["INSTANCE2", "tomcat", "3.141592", "42.23"],
            ],
            [(2, "ERROR HTTP404 No response from server or whatever")],
        ),
        (
            "INSTANCE2",
            {},
            [
                [
                    "Error:",
                    "mk_jolokia",
                    "requires",
                    "either",
                    "the",
                    "json",
                    "or",
                    "simplejson",
                    "library.",
                    "Please",
                    "either",
                    "use",
                    "a",
                    "Python",
                    "version",
                    "that",
                    "contains",
                    "the",
                    "json",
                    "library",
                    "or",
                    "install",
                    "the",
                    "simplejson",
                    "library",
                    "on",
                    "the",
                    "monitored",
                    "system.",
                ],
                ["INSTANCE1", "ERROR", "HTTP404 No response from server or whatever"],
                ["INSTANCE2", "tomcat", "3.141592", "42.23"],
            ],
            [(0, "Tomcat 3.141592 (Jolokia version 42.23)")],
        ),
    ],
)
def test_check_jolokia_info(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for jolokia_info check."""
    parsed = parse_jolokia_info(string_table)
    result = list(check_jolokia_info(item, params, parsed))
    assert result == expected_results
