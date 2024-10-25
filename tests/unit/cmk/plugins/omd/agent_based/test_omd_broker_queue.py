#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import Result, State
from cmk.plugins.omd.agent_based.omd_broker_queue import check, parse

STRINGTABLE: StringTable = [
    [
        "heute "
        '[{"name":"cmk.intersite.heute_remote_1","messages":1},{"name":"cmk.intersite.heute_remote_2","messages":2},{"name":"cmk.app.piggyback-hub.payload","messages":3},{"name":"cmk.app.piggyback-hub.config","messages":4}]'
    ],
    [
        "heute_remote_1 "
        '[{"name":"cmk.app.piggyback-hub.payload","messages":0},{"name":"cmk.intersite.heute","messages":0},{"name":"cmk.app.piggyback-hub.config","messages":0}]'
    ],
    [
        "heute_remote_2 "
        '[{"name":"cmk.app.piggyback-hub.payload","messages":0},{"name":"cmk.app.piggyback-hub.config","messages":0}]'
    ],
]


@pytest.mark.parametrize(
    "item, expected",
    [
        (
            "heute piggyback-hub",
            [
                Result(state=State.OK, summary="Messages in queue 'payload': 3"),
                Result(state=State.OK, summary="Messages in queue 'config': 4"),
            ],
        ),
        (
            "heute intersite",
            [],
        ),
        (
            "heute_remote_1 piggyback-hub",
            [
                Result(state=State.OK, summary="Messages in queue 'payload': 0"),
                Result(state=State.OK, summary="Messages in queue 'config': 0"),
            ],
        ),
    ],
)
def test_check_broker_queue(item: str, expected: list[Result]) -> None:
    assert list(check(item, parse(STRINGTABLE))) == expected
