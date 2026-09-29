#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.hp_proliant_temp import (
    check_hp_proliant_temp,
    inventory_hp_proliant_temp,
    parse_hp_proliant_temp,
)


def test_hp_proliant_temp_ignores_rows_without_sensor() -> None:
    # The iLO returns rows where only the status column is filled.
    section = parse_hp_proliant_temp(
        [
            ["1", "11", "20", "42", "2"],
            ["", "", "", "", "2"],
            ["4", "7", "33", "90", "2"],
        ]
    )
    assert list(inventory_hp_proliant_temp(section)) == [("1 (ambient)", {}), ("4 (memory)", {})]
    assert check_hp_proliant_temp("4 (memory)", {}, section)[0] == 0
