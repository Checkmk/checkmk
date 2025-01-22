#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.cisco_sma.agent_based.files_and_sockets import _check_files_and_sockets, Params


def test_check_files_and_sockets_with_no_levels() -> None:
    assert list(
        _check_files_and_sockets(
            params=Params(
                levels_upper=("no_levels", None),
                levels_lower=("no_levels", None),
            ),
            section=100,
        ),
    ) == [
        Result(state=State.OK, summary="Open: 100"),
        Metric("cisco_sma_files_and_sockets", 100.0),
    ]


def test_check_files_and_sockets_with_levels() -> None:
    assert list(
        _check_files_and_sockets(
            params=Params(
                levels_upper=("fixed", (5500.0, 6000.0)),
                levels_lower=("fixed", (0.0, 0.0)),
            ),
            section=88.8,
        ),
    ) == [
        Result(state=State.OK, summary="Open: 88"),
        Metric("cisco_sma_files_and_sockets", 88.8, levels=(5500.0, 6000.0)),
    ]
