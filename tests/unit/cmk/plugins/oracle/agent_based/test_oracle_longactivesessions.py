#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.oracle_longactivesessions import (
    check_oracle_longactivesessions,
    inventory_oracle_longactivesessions,
    parse_oracle_longactivesessions,
)

from cmk.agent_based.v2 import Metric, Result, Service, State

INFO = [
    ["orcl", "TUX12C", "Serial Number", "machine", "0", "osuser", "4800", "19", "0"],
    [
        "orcl",
        "TUX12C",
        "Another Serial Number",
        "machine",
        "0",
        "another osuser",
        "4800",
        "500",
        "0",
    ],
    [
        "orcl1",
        "TUX12C1",
        "Yet Another Serial Number",
        "another machine",
        "0",
        "yet another osuser",
        "5800",
        "500",
        "0",
    ],
]


def test_discovery() -> None:
    assert list(inventory_oracle_longactivesessions(parse_oracle_longactivesessions(INFO))) == [
        Service(item="orcl"),
        Service(item="orcl"),
        Service(item="orcl1"),
    ]


def test_check() -> None:
    assert list(
        check_oracle_longactivesessions(
            "orcl", {"levels": (500, 1000)}, parse_oracle_longactivesessions(INFO)
        )
    ) == [
        Result(state=State.OK, summary="2"),
        Metric("count", 2, levels=(500, 1000)),
        Result(
            state=State.OK,
            notice="Session (sid,serial,proc) TUX12C Another Serial Number 0 active for 8 minutes 20 seconds from machine osuser another osuser program 4800 sql_id 0 ",
        ),
    ]

    result = list(
        check_oracle_longactivesessions(
            "orcl1", {"levels": (500, 1000)}, parse_oracle_longactivesessions(INFO)
        )
    )
    assert result == [
        Result(state=State.OK, summary="1"),
        Metric("count", 1, levels=(500, 1000)),
        Result(
            state=State.OK,
            notice="Session (sid,serial,proc) TUX12C1 Yet Another Serial Number 0 active for 8 minutes 20 seconds from another machine osuser yet another osuser program 5800 sql_id 0 ",
        ),
    ]
