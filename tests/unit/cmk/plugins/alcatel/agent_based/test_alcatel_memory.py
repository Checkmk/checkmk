#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.alcatel.agent_based.alcatel_memory import (
    check_alcatel_memory,
    Params,
    parse_alcatel_memory,
)

_SPEC_DEFAULT_PARAMS = Params(levels=("fixed", (80.0, 90.0)))


def test_switch_without_health_data_yields_no_section() -> None:
    assert parse_alcatel_memory([]) is None


def test_first_module_is_monitored_on_multi_module_switch() -> None:
    assert parse_alcatel_memory([["34"], ["71"]]) == 34.0


def test_ram_usage_is_reported_in_percent_with_metric() -> None:
    results = list(check_alcatel_memory(_SPEC_DEFAULT_PARAMS, 45.0))

    assert results == [
        Result(state=State.OK, summary="Usage: 45.00%"),
        Metric("mem_used_percent", 45.0, levels=(80.0, 90.0)),
    ]


@pytest.mark.parametrize(
    "ram_usage, expected_state",
    [
        pytest.param(79.0, State.OK, id="below warn"),
        pytest.param(80.0, State.WARN, id="at warn"),
        pytest.param(90.0, State.CRIT, id="at crit"),
    ],
)
def test_ram_usage_state_follows_upper_levels(ram_usage: float, expected_state: State) -> None:
    result, _metric = check_alcatel_memory(_SPEC_DEFAULT_PARAMS, ram_usage)

    assert isinstance(result, Result)
    assert result.state is expected_state
