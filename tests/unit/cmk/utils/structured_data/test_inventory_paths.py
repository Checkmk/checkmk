#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import InventoryPaths


@pytest.mark.parametrize(
    "previous, current, expected_name",
    [
        pytest.param(-1, 0, "None_0", id="history-start"),
        pytest.param(123, 456, "123_456", id="pair"),
    ],
)
def test_delta_cache_tree(tmp_path: Path, previous: int, current: int, expected_name: str) -> None:
    assert (
        InventoryPaths(tmp_path).delta_cache_tree(HostName("hostname"), previous, current)
        == tmp_path / f"var/check_mk/inventory_delta_cache/hostname/{expected_name}"
    )


@pytest.mark.parametrize(
    "previous, current",
    [
        pytest.param(-2, 0, id="previous-too-low"),
        pytest.param(1, 0, id="previous-greater-current"),
        pytest.param(-1, -1, id="previous-equal-current"),
    ],
)
def test_delta_cache_tree_error(tmp_path: Path, previous: int, current: int) -> None:
    with pytest.raises(ValueError):
        InventoryPaths(tmp_path).delta_cache_tree(HostName("hostname"), previous, current)
