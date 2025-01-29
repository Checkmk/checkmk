#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.gerrit.agent_based import gerrit_version


def test_parse_gerrit_version() -> None:
    string_table = [
        ['{"current": "1.2.3", "latest": {"major": null, "minor": "1.3.4", "patch": "1.2.5"}}']
    ]

    value = gerrit_version.parse_gerrit_version(string_table)
    expected = gerrit_version.VersionInfo(
        current="1.2.3", latest={"major": None, "minor": "1.3.4", "patch": "1.2.5"}
    )

    assert value == expected


def test_check_gerrit_version() -> None:
    params = gerrit_version.CheckParams(
        major=State.OK.value, minor=State.OK.value, patch=State.WARN.value
    )
    section = gerrit_version.VersionInfo(
        current="1.2.3", latest={"major": None, "minor": "1.3.4", "patch": "1.2.5"}
    )

    value = list(gerrit_version.check_gerrit_version(params, section))
    expected = [
        Result(state=State.OK, summary="Current: 1.2.3"),
        Result(state=State.OK, notice="No new major release available."),
        Result(
            state=State.OK,
            notice="Latest minor release: 1.3.4 https://www.gerritcodereview.com/1.3.html ",
        ),
        Result(
            state=State.WARN,
            summary="Latest patch release: 1.2.5 https://www.gerritcodereview.com/1.2.html#125 ",
        ),
    ]

    assert value == expected
