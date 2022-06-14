#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .test_ibm_mq_include import parse_info

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_plugin"


def test_parse() -> None:
    lines = """\
version: 2.0.4
dspmq: OK
runmqsc: Not executable
"""
    section = parse_info(lines, chr(58))
    check = Check(CHECK_NAME)
    actual = check.run_parse(section)
    expected = {
        "version": "2.0.4",
        "dspmq": "OK",
        "runmqsc": "Not executable",
    }
    assert actual == expected


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
                (0, "Plugin version: 2.0.4"),
                (0, "dspmq: OK"),
                (0, "runmqsc: OK"),
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
                (0, "Plugin version: 2.0.4"),
                (0, "dspmq: OK"),
                (2, "runmqsc: Not found"),
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
                (0, "Plugin version: 2.0.4"),
                (3, "dspmq: No agent info"),
                (2, "runmqsc: Not found"),
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
                (2, "Plugin version: 2.0.4 (should be at least 2.1)"),
                (0, "dspmq: OK"),
                (2, "runmqsc: Not found"),
            ],
            id="version_mismatch",
        ),
    ],
)
def test_check(params, parsed, expected) -> None:
    check = Check(CHECK_NAME)
    actual = list(check.run_check(None, params, parsed))
    assert actual == expected
