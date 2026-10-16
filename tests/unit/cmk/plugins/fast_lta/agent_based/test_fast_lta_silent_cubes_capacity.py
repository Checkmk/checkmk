#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.fast_lta.agent_based.fast_lta_silent_cubes import (
    check_fast_lta_silent_cubes_capacity,
    discover_fast_lta_silent_cubes_capacity,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

info = [["8001591181312", "3875508482048"]]


@pytest.fixture(name="value_store")
def fixture_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, object] = {"Total.delta": (0, 3695972.90234375)}
    monkeypatch.setattr(
        "cmk.plugins.fast_lta.agent_based.fast_lta_silent_cubes.get_value_store",
        lambda: store,
    )


def test_discovery_fast_lta_silent_cube_capacity() -> None:
    assert list(discover_fast_lta_silent_cubes_capacity(info)) == [Service(item="Total")]


@pytest.mark.usefixtures("value_store")
def test_check_fast_lta_silent_cube_capacity() -> None:
    actual_check_results = list(
        check_fast_lta_silent_cubes_capacity("Total", FILESYSTEM_DEFAULT_PARAMS, info)
    )
    results = [r for r in actual_check_results if isinstance(r, Result)]
    assert results[0] == Result(state=State.OK, summary="Used: 48.43% - 3.52 TiB of 7.28 TiB")

    metrics = [m for m in actual_check_results if isinstance(m, Metric)]
    assert metrics[0].name == "fs_used"
    assert metrics[0].value == 3695972.90234375


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="Crash report 8aca83da-fb3b-11f0-ace5-2a2e0f3d4944: ValueError",
)
def test_check_fast_lta_silent_cube_capacity_empty_used_value() -> None:
    # Crash group 4562: the device reported its total capacity but an empty
    # value for the used capacity.
    assert list(
        check_fast_lta_silent_cubes_capacity(
            "Total", FILESYSTEM_DEFAULT_PARAMS, [["200021140045824", ""]]
        )
    ) == [
        Result(
            state=State.UNKNOWN,
            summary="Cannot parse capacity: got total '200021140045824', used '' (expected integers)",
        ),
    ]
