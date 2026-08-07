#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.nimble.agent_based.nimble_volumes import (
    _check_nimble_volumes,
    discover_nimble_volumes,
    parse_nimble_volumes,
)

STRING_TABLE = [
    ["1", "vol-ok", "1073741824", "536870912", "1"],
    ["", "vol-empty-size", "", "", ""],
]


def test_discovery_skips_volumes_without_size_data() -> None:
    section = parse_nimble_volumes(STRING_TABLE)
    assert list(discover_nimble_volumes(section)) == [Service(item="vol-ok")]


def test_check_ok_volume() -> None:
    section = parse_nimble_volumes(STRING_TABLE)
    results = list(
        _check_nimble_volumes(
            "vol-ok", FILESYSTEM_DEFAULT_PARAMS, section, 60.0, {"vol-ok.delta": (0, 0)}
        )
    )
    assert Metric("fs_size", 1073741824.0, boundaries=(0.0, None)) in results
    assert Result(state=State.OK, summary="Used: 50.00% - 512 TiB of 1.00 PiB") in results


def test_check_does_not_crash_on_empty_size_values() -> None:
    section = parse_nimble_volumes(STRING_TABLE)
    assert not list(
        _check_nimble_volumes("vol-empty-size", FILESYSTEM_DEFAULT_PARAMS, section, 60.0, {})
    )
