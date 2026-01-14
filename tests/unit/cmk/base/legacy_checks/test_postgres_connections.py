#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.postgres_connections import (
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
            [("app", {}), ("app_test", {}), ("postgres", {})],
        ),
    ],
)
def test_discover_postgres_connections(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for postgres_connections check."""

    parsed = parse_dbs(info)
    result = list(discover_postgres_connections(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
            [
                (
                    0,
                    "Used active connections: 0",
                    [("active_connections", 0.0, None, None, 0, 100.0)],
                ),
                (0, "Used active percentage: 0%", []),
                (0, "Used idle connections: 1", [("idle_connections", 1.0, None, None, 0, 100.0)]),
                (0, "Used idle percentage: 1.00%", []),
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
            [
                (
                    0,
                    "Used active connections: 0",
                    [("active_connections", 0.0, None, None, 0, 100.0)],
                ),
                (0, "Used active percentage: 0%", []),
                (0, "Used idle connections: 2", [("idle_connections", 2.0, None, None, 0, 100.0)]),
                (1, "Used idle percentage: 2.00% (warn/crit at 1.00%/5.00%)", []),
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
                (
                    2,
                    "Used active connections: 9 (warn/crit at 2/5)",
                    [("active_connections", 9.0, 2, 5, 0, 100.0)],
                ),
                (0, "Used active percentage: 9.00%", []),
                (0, "Used idle connections: 4", [("idle_connections", 4.0, None, None, 0, 100.0)]),
                (0, "Used idle percentage: 4.00%", []),
            ],
        ),
    ],
)
def test_check_postgres_connections(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for postgres_connections check."""

    parsed = parse_dbs(info)
    result = list(check_postgres_connections(item, params, parsed))
    assert result == expected_results
