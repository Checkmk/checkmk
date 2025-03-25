#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.memory_utilization import (
    _check_memory_utilization,
    _discover_memory_utilization,
    Params,
)


def test_discovery() -> None:
    assert list(_discover_memory_utilization(12.34)) == [Service()]


def test_check() -> None:
    assert list(_check_memory_utilization(Params(levels=("fixed", (50, 70))), 70)) == [
        Result(state=State.CRIT, summary="Utilization: 70.00% (warn/crit at 50.00%/70.00%)"),
        Metric("mem_used_percent", 70.0, levels=(50.0, 70.0)),
    ]
