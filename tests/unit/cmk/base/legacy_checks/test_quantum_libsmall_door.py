#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.legacy_checks.quantum_libsmall_door import (
    check_quantum_libsmall_door,
    inventory_quantum_libsmall_door,
    parse_quantum_libsmall_door,
)


@pytest.mark.parametrize(
    ["string_table", "expected"],
    [pytest.param([], None, id="empty"), pytest.param([["1"]], [["1"]], id="non-empty")],
)
def test_parse_quantum_libsmall_door(
    string_table: list[list[str]], expected: list[list[str]] | None
) -> None:
    assert expected == (parse_quantum_libsmall_door(string_table))


def test_inventory_quantum_libsmall_door():
    assert [(None, None)] == list(inventory_quantum_libsmall_door(None))


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param([["1"]], [2, "Library door open"], id="open"),
        pytest.param([["2"]], [0, "Library door closed"], id="closed"),
        pytest.param([["something"]], [3, "Library door status unknown"], id="unknown"),
    ],
)
def test_check_quantum_libsmall_door(section, expected):
    assert expected == list(check_quantum_libsmall_door(None, None, section))
