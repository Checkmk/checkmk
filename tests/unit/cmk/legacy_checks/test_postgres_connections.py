#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.postgres_connections import (
    check_postgres_connections,
    discover_postgres_connections,
)
from cmk.plugins.postgres.lib import parse_dbs


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                ["[databases_start]"],
                ["postgres"],
                ["app"],
                ["app_test"],
                ["[databases_end]"],
                ["datname", "mc", "idle", "active"],
                ["postgres", "100", "4", "9"],
                ["", "100", "0", "0"],
                ["app", "100", "1", "0"],
                ["app_test", "100", "2", "0"],
            ],
            [Service(item="app"), Service(item="app_test"), Service(item="postgres")],
        ),
    ],
)
def test_discover_postgres_connections(
    info: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_dbs(info)
    result = list(discover_postgres_connections(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "app",
            {"levels_perc_active": (80.0, 90.0), "levels_perc_idle": (80.0, 90.0)},
            [
                ["[databases_start]"],
                ["postgres"],
                ["app"],
                ["app_test"],
                ["[databases_end]"],
                ["datname", "mc", "idle", "active"],
                ["postgres", "100", "4", "9"],
                ["", "100", "0", "0"],
                ["app", "100", "1", "0"],
                ["app_test", "100", "2", "0"],
            ],
            # active=0 (not skipped because "0" is truthy), idle=1
            [
                Result(state=State.OK, summary="Used active connections: 0"),
                Metric("active_connections", 0.0, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used active percentage: 0%"),
                Result(state=State.OK, summary="Used idle connections: 1"),
                Metric("idle_connections", 1.0, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used idle percentage: 1.00%"),
            ],
        ),
        (
            "app_test",
            {"levels_perc_active": (80.0, 90.0), "levels_perc_idle": (1.0, 5.0)},
            [
                ["[databases_start]"],
                ["postgres"],
                ["app"],
                ["app_test"],
                ["[databases_end]"],
                ["datname", "mc", "idle", "active"],
                ["postgres", "100", "4", "9"],
                ["", "100", "0", "0"],
                ["app", "100", "1", "0"],
                ["app_test", "100", "2", "0"],
            ],
            # active=0 (not skipped); idle=2, perc=2% warns
            [
                Result(state=State.OK, summary="Used active connections: 0"),
                Metric("active_connections", 0.0, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used active percentage: 0%"),
                Result(state=State.OK, summary="Used idle connections: 2"),
                Metric("idle_connections", 2.0, boundaries=(0.0, 100.0)),
                Result(
                    state=State.WARN,
                    summary="Used idle percentage: 2.00% (warn/crit at 1.00%/5.00%)",
                ),
            ],
        ),
        (
            "postgres",
            {
                "levels_perc_active": (80.0, 90.0),
                "levels_perc_idle": (80.0, 90.0),
                "levels_abs_active": (2, 5),
            },
            [
                ["[databases_start]"],
                ["postgres"],
                ["app"],
                ["app_test"],
                ["[databases_end]"],
                ["datname", "mc", "idle", "active"],
                ["postgres", "100", "4", "9"],
                ["", "100", "0", "0"],
                ["app", "100", "1", "0"],
                ["app_test", "100", "2", "0"],
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Used active connections: 9 (warn/crit at 2/5)",
                ),
                Metric("active_connections", 9.0, levels=(2.0, 5.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used active percentage: 9.00%"),
                Result(state=State.OK, summary="Used idle connections: 4"),
                Metric("idle_connections", 4.0, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used idle percentage: 4.00%"),
            ],
        ),
    ],
)
def test_check_postgres_connections(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    parsed = parse_dbs(info)
    result = list(check_postgres_connections(item, params, parsed))
    assert result == expected_results
