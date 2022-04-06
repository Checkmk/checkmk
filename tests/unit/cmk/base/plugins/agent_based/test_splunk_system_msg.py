#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.api.agent_based.checking_classes import Result, State
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.splunk_system_msg import check, parse, Section, SplunkMessage


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
                ["foo", "info", "host", "2019-05-16T08:32:33+02:00", "", "simple"],
                ["foo", "crit", "host", "2019-05-16T08:32:33+02:00", "", "complex"],
            ],
            [
                SplunkMessage(
                    name="foo",
                    severity="info",
                    server="host",
                    timeCreated_iso="2019-05-16T08:32:33+02:00",
                    message="simple",
                ),
                SplunkMessage(
                    name="foo",
                    severity="crit",
                    server="host",
                    timeCreated_iso="2019-05-16T08:32:33+02:00",
                    message="complex",
                ),
            ],
            id="multiple message",
        ),
        pytest.param(
            [["foo", "info", "host", "2019-05-16T08:32:33+02:00", "", "simple"]],
            [
                SplunkMessage(
                    name="foo",
                    severity="info",
                    server="host",
                    timeCreated_iso="2019-05-16T08:32:33+02:00",
                    message="simple",
                )
            ],
            id="short message",
        ),
        pytest.param(
            [
                [
                    "foo",
                    "info",
                    "host",
                    "2019-05-16T08:32:33+02:00",
                    "",
                    "simple",
                    "separated",
                    "by",
                    "spaces",
                ]
            ],
            [
                SplunkMessage(
                    name="foo",
                    severity="info",
                    server="host",
                    timeCreated_iso="2019-05-16T08:32:33+02:00",
                    message="simple separated by spaces",
                )
            ],
            id="short message",
        ),
    ],
)
def test_parsing(string_table: StringTable, section: Section):
    assert parse(string_table) == section


@pytest.mark.parametrize(
    "section ,results",
    [
        pytest.param(
            [SplunkMessage("foo", "info", "host", "2019-05-16T08:32:33+02:00", "msg")],
            [Result(state=State.OK, summary="2019-05-16T08:32:33+02:00 - host - msg")],
            id="single message",
        ),
        pytest.param(
            [
                SplunkMessage("foo", "info", "host", "2019-05-16T08:32:33+02:00", "msg"),
                SplunkMessage("bar", "info", "host", "2019-05-16T08:32:33+02:00", "msg2"),
            ],
            [
                Result(state=State.OK, summary="2019-05-16T08:32:33+02:00 - host - msg"),
                Result(state=State.OK, summary="2019-05-16T08:32:33+02:00 - host - msg2"),
            ],
            id="multiple message",
        ),
        pytest.param(
            [SplunkMessage("foo", "warn", "host", "2019-05-16T08:32:33+02:00", "msg")],
            [Result(state=State.WARN, summary="2019-05-16T08:32:33+02:00 - host - msg")],
            id="warn",
        ),
        pytest.param(
            [SplunkMessage("foo", "error", "host", "2019-05-16T08:32:33+02:00", "msg")],
            [Result(state=State.CRIT, summary="2019-05-16T08:32:33+02:00 - host - msg")],
            id="crit",
        ),
        pytest.param(
            [SplunkMessage("foo", "nope", "host", "2019-05-16T08:32:33+02:00", "msg")],
            [Result(state=State.UNKNOWN, summary="2019-05-16T08:32:33+02:00 - host - msg")],
            id="unkown",
        ),
    ],
)
def test_check(section: Section, results: list[Result]):
    assert list(check(section)) == results
