#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.cisco_sma.agent_based.files_and_sockets import (
    _check_files_and_sockets,
    _discover_files_and_sockets,
    _parse_files_and_sockets,
    Params,
)


def test_discover_files_and_sockets() -> None:
    assert list(_discover_files_and_sockets(100)) == [Service()]


def test_check_files_and_sockets_with_no_levels() -> None:
    assert list(
        _check_files_and_sockets(
            params=Params(
                levels_upper_open_files_and_sockets=("no_levels", None),
                levels_lower_open_files_and_sockets=("no_levels", None),
            ),
            section=100,
        ),
    ) == [
        Result(state=State.OK, summary="Open: 100"),
        Metric("cisco_sma_files_and_sockets", 100),
    ]


def test_check_files_and_sockets_with_levels() -> None:
    assert list(
        _check_files_and_sockets(
            params=Params(
                levels_upper_open_files_and_sockets=("fixed", (5500, 6000)),
                levels_lower_open_files_and_sockets=("fixed", (0, 0)),
            ),
            section=88,
        ),
    ) == [
        Result(state=State.OK, summary="Open: 88"),
        Metric("cisco_sma_files_and_sockets", 88, levels=(5500, 6000)),
    ]


def test__parse_files_and_sockets() -> None:
    assert _parse_files_and_sockets([["1"]]) == 1
    assert _parse_files_and_sockets([[]]) is None
