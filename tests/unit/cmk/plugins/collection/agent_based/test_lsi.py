#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.collection.agent_based.lsi import (
    check_plugin_lsi_array,
    check_plugin_lsi_disk,
    parse_lsi,
)

INFO = [
    ["VolumeID", "286"],
    ["Statusofvolume", "Okay(OKY)"],
    ["TargetID", "15"],
    ["State", "Optimal(OPT)"],
    ["TargetID", "1"],
    ["State", "Optimal(OPT)"],
]


def test_lsi_parsing() -> None:
    result = parse_lsi(INFO)
    assert "disks" in result and "arrays" in result
    assert "286" in result["arrays"]
    assert "1" in result["disks"]
    assert result["disks"]["1"] == "OPT"


def test_lsi_array_discovery() -> None:
    section = parse_lsi(INFO)
    assert list(check_plugin_lsi_array.discovery_function(section=section)) == [Service(item="286")]


def test_lsi_disk_discovery() -> None:
    section = parse_lsi(INFO)
    assert list(check_plugin_lsi_disk.discovery_function(section=section)) == [
        Service(item="15", parameters={"expected_state": "OPT"}),
        Service(item="1", parameters={"expected_state": "OPT"}),
    ]


def test_lsi_array() -> None:
    section = parse_lsi(INFO)
    assert list(check_plugin_lsi_array.check_function(item="286", params={}, section=section)) == [
        Result(state=State.OK, summary="Status is 'Okay(OKY)'")
    ]


@pytest.mark.parametrize(
    "item,params,expected",
    [
        (
            "1",
            {"expected_state": "OPT"},
            [Result(state=State.OK, summary="Disk has state 'OPT'")],
        ),
        (
            "15",
            {"expected_state": "OPT"},
            [Result(state=State.OK, summary="Disk has state 'OPT'")],
        ),
    ],
)
def test_lsi(
    item: str,
    params: Mapping[str, str],
    expected: CheckResult,
) -> None:
    section = parse_lsi(INFO)
    assert (
        list(
            check_plugin_lsi_disk.check_function(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected
    )
