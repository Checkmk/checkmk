#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.steelhead_status import (
    check_steelhead_status,
    discover_steelhead_status,
    parse_steelhead_status,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        pytest.param([["Healthy", "running"]], [Service()], id="one row yields the service"),
        pytest.param([], [], id="no row yields nothing"),
    ],
)
def test_discovery_yields_service_only_for_exactly_one_row(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    section = parse_steelhead_status(string_table)

    result = list(discover_steelhead_status(section))

    assert result == expected_discoveries


def test_check_is_ok_when_healthy_and_running() -> None:
    section = parse_steelhead_status([["Healthy", "running"]])

    result = list(check_steelhead_status(section))

    assert result == [Result(state=State.OK, summary="Healthy and running")]


@pytest.mark.parametrize(
    "string_table, expected_summary",
    [
        pytest.param([["Degraded", "running"]], "Status is Degraded and running", id="unhealthy"),
        pytest.param([["Healthy", "stopped"]], "Status is Healthy and stopped", id="not running"),
    ],
)
def test_check_is_crit_unless_healthy_and_running(
    string_table: StringTable, expected_summary: str
) -> None:
    section = parse_steelhead_status(string_table)

    result = list(check_steelhead_status(section))

    assert result == [Result(state=State.CRIT, summary=expected_summary)]
