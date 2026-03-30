#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.legacy_checks.ibm_mq_plugin import (
    check_ibm_mq_plugin,
    discover_ibm_mq_plugin,
    parse_ibm_mq_plugin,
)

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_plugin"


def parse_info(lines: str, separator: str | None = None) -> list[list[str]]:
    result = []
    for line in lines.splitlines():
        line = line.strip()
        result.append(line.split(separator))
    return result


def test_parse() -> None:
    lines = """\
version: 2.0.4
dspmq: OK
runmqsc: Not executable
"""
    section = parse_info(lines, chr(58))
    actual = parse_ibm_mq_plugin(section)
    expected = {
        "version": "2.0.4",
        "dspmq": "OK",
        "runmqsc": "Not executable",
    }
    assert actual == expected


def test_discover() -> None:
    parsed = {
        "version": "2.0.4",
        "dspmq": "OK",
        "runmqsc": "OK",
    }
    discovery = list(discover_ibm_mq_plugin(parsed))
    assert len(discovery) == 1
    assert Service() in discovery


def test_discover_empty() -> None:
    discovery = list(discover_ibm_mq_plugin({}))
    assert discovery == []


@pytest.mark.parametrize(
    "params, parsed, expected",
    [
        pytest.param(
            {},
            {
                "version": "2.0.4",
                "dspmq": "OK",
                "runmqsc": "OK",
            },
            [
                Result(state=State.OK, summary="Plugin version: 2.0.4"),
                Result(state=State.OK, summary="dspmq: OK"),
                Result(state=State.OK, summary="runmqsc: OK"),
            ],
            id="all_ok",
        ),
        pytest.param(
            {},
            {
                "version": "2.0.4",
                "dspmq": "OK",
                "runmqsc": "Not found",
            },
            [
                Result(state=State.OK, summary="Plugin version: 2.0.4"),
                Result(state=State.OK, summary="dspmq: OK"),
                Result(state=State.CRIT, summary="runmqsc: Not found"),
            ],
            id="one_tool_not_found",
        ),
        pytest.param(
            {},
            {
                "version": "2.0.4",
                "runmqsc": "Not found",
            },
            [
                Result(state=State.OK, summary="Plugin version: 2.0.4"),
                Result(state=State.UNKNOWN, summary="dspmq: No agent info"),
                Result(state=State.CRIT, summary="runmqsc: Not found"),
            ],
            id="tool_not_in_agent",
        ),
        pytest.param(
            {"version": (("at_least", "2.1"), 2)},
            {
                "version": "2.0.4",
                "dspmq": "OK",
                "runmqsc": "Not found",
            },
            [
                Result(state=State.CRIT, summary="Plugin version: 2.0.4 (should be at least 2.1)"),
                Result(state=State.OK, summary="dspmq: OK"),
                Result(state=State.CRIT, summary="runmqsc: Not found"),
            ],
            id="version_mismatch",
        ),
    ],
)
def test_check(
    params: Mapping[str, object],
    parsed: dict[str, str],
    expected: list[Result],
) -> None:
    actual = list(check_ibm_mq_plugin(params, parsed))
    assert actual == expected
