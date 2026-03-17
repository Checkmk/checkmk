#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.checkpoint_svn_status import (
    check_checkpoint_svn_status,
    discover_checkpoint_svn_status,
)


def test_discover_yields_service() -> None:
    assert list(discover_checkpoint_svn_status([["9", "7", "0", "OK"]])) == [Service()]


def test_discover_empty_section() -> None:
    assert list(discover_checkpoint_svn_status([])) == []


@pytest.mark.parametrize(
    "section, expected",
    [
        (
            [["9", "7", "0", "OK"]],
            [Result(state=State.OK, summary="OK (v9.7)")],
        ),
        (
            [["9", "7", "1", "SVN error"]],
            [Result(state=State.CRIT, summary="SVN error")],
        ),
        # OIDs 101 (code) and 103 (description) missing — version only
        (
            [["9", "7", "", ""]],
            [Result(state=State.OK, summary="OK (v9.7)")],
        ),
    ],
)
def test_check_checkpoint_svn_status(section: list[list[str]], expected: list[Result]) -> None:
    assert list(check_checkpoint_svn_status(section)) == expected
