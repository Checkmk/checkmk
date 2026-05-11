#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.hp_proliant_cpu import (
    check_hp_proliant_cpu,
    discover_hp_proliant_cpu,
    parse_hp_proliant_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["0", "0", "Intel Xeon", "2"], ["1", "0", "Intel Xeon", "2"]],
            [Service(item="0"), Service(item="1")],
        ),
    ],
)
def test_discover_hp_proliant_cpu(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_hp_proliant_cpu(string_table)
    assert sorted(discover_hp_proliant_cpu(parsed), key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "0",
            [["0", "0", "Intel Xeon", "2"], ["1", "0", "Intel Xeon", "2"]],
            [Result(state=State.OK, summary='CPU0 "Intel Xeon" in slot 0 is in state "ok"')],
        ),
        (
            "1",
            [["0", "0", "Intel Xeon", "2"], ["1", "0", "Intel Xeon", "2"]],
            [Result(state=State.OK, summary='CPU1 "Intel Xeon" in slot 0 is in state "ok"')],
        ),
    ],
)
def test_check_hp_proliant_cpu(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    parsed = parse_hp_proliant_cpu(string_table)
    assert list(check_hp_proliant_cpu(item, parsed)) == expected_results
