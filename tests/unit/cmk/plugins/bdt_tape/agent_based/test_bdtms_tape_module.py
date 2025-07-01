#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.bdt_tape.agent_based.bdtms_tape_module import (
    check_bdtms_tape_module,
    discover_bdtms_tape_module,
    parse_bdtms_tape_module,
)

_SECTION = parse_bdtms_tape_module(
    [
        ["1", "OK", "OK", "OK"],
        ["2", "OK", "OK", "OK"],
        [
            "3",
            "BROKEN",  # probably not a realistic value, but sufficient for testing
            "OK",
            "OK",
        ],
    ]
)


def test_discover_bdtms_tape_module() -> None:
    assert list(discover_bdtms_tape_module(_SECTION)) == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
    ]


def test_check_bdtms_tape_module_all_ok() -> None:
    assert list(check_bdtms_tape_module("1", _SECTION)) == [
        Result(state=State.OK, summary="Module: ok"),
        Result(state=State.OK, summary="Board: ok"),
        Result(state=State.OK, summary="Power supply: ok"),
    ]


def test_check_bdtms_tape_module_with_issues() -> None:
    assert list(check_bdtms_tape_module("3", _SECTION)) == [
        Result(state=State.CRIT, summary="Module: broken"),
        Result(state=State.OK, summary="Board: ok"),
        Result(state=State.OK, summary="Power supply: ok"),
    ]


def test_check_bdtms_tape_module_item_missing() -> None:
    assert not list(check_bdtms_tape_module("missing", _SECTION))
