#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.nimble_volumes import (
    _check_nimble_volumes,
    inventory_nimble_volumes,
    parse_nimble_volumes,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

from .checktestlib import mock_item_state

STRING_TABLE = [
    ["1", "vol-ok", "1073741824", "536870912", "1"],
    ["", "vol-empty-size", "", "", ""],
]


def test_discovery_skips_volumes_without_size_data() -> None:
    section = parse_nimble_volumes(STRING_TABLE)
    assert list(inventory_nimble_volumes(section)) == [("vol-ok", {})]


def test_check_ok_volume() -> None:
    section = parse_nimble_volumes(STRING_TABLE)
    with mock_item_state({"df.vol-ok.delta": (0, 0)}):
        results = list(_check_nimble_volumes("vol-ok", FILESYSTEM_DEFAULT_PARAMS, section, 60.0))
    assert len(results) == 1
    state, summary, perfdata = results[0]
    assert state == 0
    assert summary.startswith("Used: 50.00% - 512 TiB of 1.00 PiB")
    assert ("fs_size", 1073741824, None, None, 0, None) in perfdata


def test_check_does_not_crash_on_empty_size_values() -> None:
    section = parse_nimble_volumes(STRING_TABLE)
    assert not list(
        _check_nimble_volumes("vol-empty-size", FILESYSTEM_DEFAULT_PARAMS, section, 60.0)
    )
