#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.viprinet.rulesets.viprinet_router import _migrate_expect_mode


@pytest.mark.parametrize(
    "legacy, expected",
    [
        ("0", "node"),
        ("1", "hub"),
        ("2", "hub_hotspare"),
        ("3", "hub_hotspare_replacing"),
        ("inv", "inventory"),
    ],
)
def test_migrate_expect_mode_from_legacy(legacy: str, expected: str) -> None:
    assert _migrate_expect_mode(legacy) == expected


@pytest.mark.parametrize(
    "value",
    [
        "node",
        "hub",
        "hub_hotspare",
        "hub_hotspare_replacing",
        "inventory",
    ],
)
def test_migrate_expect_mode_already_migrated_no_op(value: str) -> None:
    assert _migrate_expect_mode(value) == value


def test_migrate_expect_mode_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        _migrate_expect_mode(123)


def test_migrate_expect_mode_rejects_unrecognized_value() -> None:
    with pytest.raises(ValueError):
        _migrate_expect_mode("unknown")
