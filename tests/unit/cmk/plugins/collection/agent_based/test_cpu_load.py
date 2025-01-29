#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.cpu import parse_cpu
from cmk.plugins.lib.cpu_load import check_cpu_load

STRING_TABLE: StringTable = [["0.88", "0.83", "0.87", "2/2148", "21050", "8"]]


def test_basic_cpu_loads() -> None:
    section = parse_cpu(STRING_TABLE)
    assert section
    result = list(
        check_cpu_load(
            params={"levels1": None, "levels5": None, "levels15": (5.0, 10.0)},
            section=section,
        )
    )
    assert result == [
        Result(state=State.OK, summary="15 min load: 0.87"),
        Metric("load15", 0.87, levels=(40.0, 80.0)),
        Result(state=State.OK, summary="15 min load per core: 0.11 (8 cores)"),
        Result(state=State.OK, notice="1 min load: 0.88"),
        Metric("load1", 0.88, boundaries=(0, 8)),
        Result(state=State.OK, notice="1 min load per core: 0.11 (8 cores)"),
        Result(state=State.OK, notice="5 min load: 0.83"),
        Metric("load5", 0.83),
        Result(state=State.OK, notice="5 min load per core: 0.10 (8 cores)"),
    ]
