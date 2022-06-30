#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Sequence

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based import lnx_quota
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

_STRING_TABLE = [
    ["[[[usr:/]]]"],
    [
        "***",
        "Report",
        "for",
        "user",
        "quotas",
        "on",
        "device",
        "/dev/mapper/volume-root",
    ],
    ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
    ["Block", "limits", "File", "limits"],
    ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
    ["----------------------------------------------------------------------"],
    ["root", "--", "6003424", "0", "0", "0", "167394", "0", "0", "0"],
    ["[[[usr:/quarktasche]]]"],
    ["***", "Report", "for", "user", "quotas", "on", "device", "/moo"],
    ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
    ["Block", "limits", "File", "limits"],
    ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
    ["----------------------------------------------------------------------"],
    ["root", "--", "6003424", "0", "0", "0", "167394", "0", "100000000", "0"],
    ["[[[grp:/nussecke]]]"],
    ["***", "Report", "for", "group", "quotas", "on", "device", "/huiboo"],
    ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
    ["Block", "limits", "File", "limits"],
    ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
    ["----------------------------------------------------------------------"],
    ["root", "--", "6003424", "0", "0", "0", "167394", "0", "100000000", "0"],
    ["www-data", "--", "4404688", "0", "0", "0", "49314", "31415", "100000000", "0"],
]


def test_parse() -> None:
    assert lnx_quota.parse(_STRING_TABLE) == {
        "/": {"usr": {"root": [6147506176, 0, 0, 0, 167394, 0, 0, 0]}},
        "/nussecke": {
            "grp": {
                "root": [6147506176, 0, 0, 0, 167394, 0, 100000000, 0],
                "www-data": [4510400512, 0, 0, 0, 49314, 31415, 100000000, 0],
            }
        },
        "/quarktasche": {"usr": {"root": [6147506176, 0, 0, 0, 167394, 0, 100000000, 0]}},
    }


def test_discover() -> None:
    assert list(lnx_quota.discover(lnx_quota.parse(_STRING_TABLE))) == [
        Service(item="/", parameters={"user": True, "group": False}),
        Service(item="/quarktasche", parameters={"user": True, "group": False}),
        Service(item="/nussecke", parameters={"user": False, "group": True}),
    ]


@pytest.mark.parametrize(
    "item, params, string_table, expected",
    [
        pytest.param(
            "/",
            lnx_quota._DEFAULT_PARAMETERS,
            _STRING_TABLE,
            [Result(state=State.OK, summary="All users within quota limits")],
            id="everything ok",
        ),
        pytest.param(
            "/",
            lnx_quota._DEFAULT_PARAMETERS,
            [
                ["[[[usr:/]]]"],
                [
                    "***",
                    "Report",
                    "for",
                    "user",
                    "quotas",
                    "on",
                    "device",
                    "/dev/mapper/volume-root",
                ],
                ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
                ["Block", "limits", "File", "limits"],
                ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
                ["----------------------------------------------------------------------"],
                ["root", "--", "6003424", "10", "0", "0", "167394", "0", "0", "0"],
            ],
            [Result(state=State.CRIT, summary="User root exceeded space hard limit 5.73 GiB/0 B")],
            id="quota limits hard reached",
        ),
        pytest.param(
            "/nussecke",
            {"group": True},
            [
                ["[[[grp:/nussecke]]]"],
                ["***", "Report", "for", "group", "quotas", "on", "device", "/huiboo"],
                ["Block", "grace", "time:", "7days;", "Inode", "grace", "time:", "7days"],
                ["Block", "limits", "File", "limits"],
                ["User", "used", "soft", "hard", "grace", "used", "soft", "hard", "grace"],
                ["----------------------------------------------------------------------"],
                ["root", "--", "6003424", "23", "0", "1", "167394", "0", "100000000", "0"],
                ["www-data", "--", "4404688", "0", "0", "0", "49314", "31415", "100000000", "0"],
            ],
            [
                Result(
                    state=State.CRIT, summary="Group root exceeded space hard limit 5.73 GiB/0 B"
                ),
                Result(
                    state=State.WARN, summary="Group www-data exceeded file soft limit 49314/31415"
                ),
            ],
            id="group soft limit and hard limit",
        ),
    ],
)
def test_check(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected: Sequence[CheckResult],
) -> None:
    assert (
        list(lnx_quota.check(item=item, params=params, section=lnx_quota.parse(string_table)))
        == expected
    )
