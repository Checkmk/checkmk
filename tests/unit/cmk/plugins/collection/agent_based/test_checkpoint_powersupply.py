#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.checkpoint_powersupply import (
    check_checkpoint_powersupply,
    check_plugin_checkpoint_powersupply,
    discover_checkpoint_powersupply,
    parse_checkpoint_powersupply,
)

DEFAULT_PARAMS = check_plugin_checkpoint_powersupply.check_default_parameters

STRING_TABLE: StringTable = [
    ["1", "Up"],
    ["2", "Up"],
    ["3", "Down"],
]


def test_parse_checkpoint_powersupply() -> None:
    assert parse_checkpoint_powersupply(STRING_TABLE) == STRING_TABLE  # for now, that is


def test_discover_checkpoint_powersupply() -> None:
    section = parse_checkpoint_powersupply(STRING_TABLE)
    assert list(discover_checkpoint_powersupply(section)) == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
    ]


def test_discover_checkpoint_powersupply_empty() -> None:
    assert list(discover_checkpoint_powersupply([])) == []


@pytest.mark.parametrize(
    "item, params, section, expected",
    [
        ("1", DEFAULT_PARAMS, [["1", "Up"]], Result(state=State.OK, summary="Up")),
        ("1", DEFAULT_PARAMS, [["1", "Down"]], Result(state=State.CRIT, summary="Down")),
        ("1", DEFAULT_PARAMS, [["1", "Present"]], Result(state=State.CRIT, summary="Present")),
        (
            "1",
            {"up": State.OK.value, "present": State.OK.value},
            [["1", "Present"]],
            Result(state=State.OK, summary="Present"),
        ),
    ],
)
def test_check_checkpoint_powersupply(
    item: str,
    params: Mapping[str, object],
    section: StringTable,
    expected: Result,
) -> None:
    assert list(check_checkpoint_powersupply(item, params, section)) == [expected]


def test_check_checkpoint_powersupply_item_not_found() -> None:
    assert DEFAULT_PARAMS is not None  # mypy
    assert list(check_checkpoint_powersupply("99", DEFAULT_PARAMS, STRING_TABLE)) == []
