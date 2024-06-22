#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.globalprotect_utilization import (
    check_globalprotect_utilization,
    discover_globalprotect_utilization,
    parse_globalprotect_utilization,
    Section,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [([[3, 250, 8]], Section(utilization=3, max_tunnels=250, active_tunnels=8)), ([[]], None)],
)
def test_parse_globalprotect_utilization(
    string_table: StringTable, expected_result: Section | None
) -> None:
    section = parse_globalprotect_utilization(string_table)
    assert section == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [(Section(utilization=3, max_tunnels=250, active_tunnels=8), [Service()])],
)
def test_discover_globalprotect_utilization(
    section: Section, expected_result: list[Service]
) -> None:
    services = list(discover_globalprotect_utilization(section))
    assert services == expected_result


@pytest.mark.parametrize(
    "params, section, expected_result",
    [
        (
            {"utilization": (1, 5)},
            Section(utilization=3, max_tunnels=250, active_tunnels=8),
            [
                Result(state=State.WARN, summary="Utilization: 3.00% (warn/crit at 1.00%/5.00%)"),
                Metric("channel_utilization", 3.0, levels=(1.0, 5.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Active sessions: 8.00"),
                Metric("active_sessions", 8.0, boundaries=(0.0, 250.0)),
                Result(state=State.OK, summary="Max sessions: 250"),
            ],
        )
    ],
)
def test_check_globalprotect_utilization(
    params: Mapping[str, Any], section: Section, expected_result: list[Metric | Result]
) -> None:
    result = list(check_globalprotect_utilization(params, section))
    assert result == expected_result
