#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.jolokia.agent_based.jolokia_info import (
    check_jolokia_info,
    discover_jolokia_info,
    parse_jolokia_info,
)

_STRING_TABLE: StringTable = [
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
]


def test_discover_jolokia_info() -> None:
    result = list(discover_jolokia_info(parse_jolokia_info(_STRING_TABLE)))
    assert result == [
        Service(item="Error:"),
        Service(item="INSTANCE1"),
        Service(item="INSTANCE2"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "Error:",
            [
                Result(
                    state=State.UNKNOWN,
                    summary=(
                        "mk_jolokia requires either the json or simplejson library. "
                        "Please either use a Python version that contains the json library "
                        "or install the simplejson library on the monitored system."
                    ),
                )
            ],
        ),
        (
            "INSTANCE1",
            [Result(state=State.CRIT, summary="ERROR HTTP404 No response from server or whatever")],
        ),
        (
            "INSTANCE2",
            [Result(state=State.OK, summary="Tomcat 3.141592 (Jolokia version 42.23)")],
        ),
    ],
)
def test_check_jolokia_info(item: str, expected_results: Sequence[Result]) -> None:
    result = list(check_jolokia_info(item, parse_jolokia_info(_STRING_TABLE)))
    assert result == expected_results
