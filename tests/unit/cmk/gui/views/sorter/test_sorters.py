#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.type_defs import Row
from cmk.gui.views.sorter import all_sorters


def _cpu_row(perf_data: str) -> Row:
    return {
        "service_perf_data": perf_data,
        "service_check_command": "check_mk-cpu_utilization_os",
    }


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    ["row1", "row2", "expected"],
    [
        pytest.param(_cpu_row("util=5;80;90"), _cpu_row("util=20.5;80;90"), -1, id="smaller"),
        pytest.param(_cpu_row("util=20.5;80;90"), _cpu_row("util=5;80;90"), 1, id="greater"),
        pytest.param(_cpu_row("util=5;80;90"), _cpu_row("util=5.0;80;90"), 0, id="equal"),
        pytest.param(_cpu_row(""), _cpu_row("util=5;80;90"), -1, id="missing_metric_first"),
        pytest.param(_cpu_row("other=99"), _cpu_row("other=1"), 0, id="unrelated_metric"),
    ],
)
def test_service_specific_metric_sorter_orders_by_metric_value(
    row1: Row, row2: Row, expected: int
) -> None:
    sorter = all_sorters(active_config)["service_specific_metric"]
    assert (
        sorter.cmp(row1, row2, parameters={"metric": "util"}, config=active_config, request=request)
        == expected
    )
