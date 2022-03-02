#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.cpu import parse_cpu
from cmk.base.plugins.agent_based.cpu_load import check_cpu_load

STRING_TABLE: StringTable = [["0.88", "0.83", "0.87", "2/2148", "21050", "8"]]


def test_basic_cpu_loads():
    section = parse_cpu(STRING_TABLE)  # type: ignore[arg-type]
    assert section
    result = list(
        check_cpu_load(
            params={"levels": (5.0, 10.0)},
            section=section,
        )
    )
    assert result == [
        Result(state=State.OK, summary="15 min load: 0.87"),
        Metric("load15", 0.87, levels=(40.0, 80.0)),
        Result(state=State.OK, summary="15 min load per core: 0.11 (8 cores)"),
        Metric("load1", 0.88, boundaries=(0.0, 8.0)),
        Metric("load5", 0.83, boundaries=(0.0, 8.0)),
    ]
