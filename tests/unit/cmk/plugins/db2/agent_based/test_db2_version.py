#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.db2.agent_based.db2_version import (
    check_db2_version,
    discover_db2_version,
    parse_db2_version,
)

SECTION = parse_db2_version(
    [
        ["db2taddm DB2v10.1.0.4,s140509(IP23577)"],
        ["db2noinfo"],
    ]
)


def test_every_instance_is_discovered() -> None:
    assert list(discover_db2_version(SECTION)) == [
        Service(item="db2taddm"),
        Service(item="db2noinfo"),
    ]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            "db2taddm",
            Result(state=State.OK, summary="DB2v10.1.0.4,s140509(IP23577)"),
            id="version reported",
        ),
        pytest.param(
            "db2noinfo",
            Result(state=State.UNKNOWN, summary="No instance information found"),
            id="no version",
        ),
        pytest.param(
            "db2gone", Result(state=State.CRIT, summary="Instance is down"), id="instance missing"
        ),
    ],
)
def test_instance_state_reflects_reported_version(item: str, expected: Result) -> None:
    assert list(check_db2_version(item, SECTION)) == [expected]
