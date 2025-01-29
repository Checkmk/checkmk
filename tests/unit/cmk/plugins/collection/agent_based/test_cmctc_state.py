#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.cmctc_state import (
    check_cmctc_state,
    inventory_cmctc_state,
    parse_cmctc_state,
)


def _section_ok() -> StringTable:
    assert (section := parse_cmctc_state([["2", "3"]])) is not None
    return section


def _section_failed() -> StringTable:
    assert (section := parse_cmctc_state([["1", "3"]])) is not None
    return section


def _section_unknown() -> StringTable:
    assert (section := parse_cmctc_state([["4", "1"]])) is not None
    return section


def test_discovery_ok() -> None:
    assert list(inventory_cmctc_state(_section_ok())) == [Service()]


def test_check_ok() -> None:
    assert list(check_cmctc_state(_section_ok())) == [
        Result(state=State.OK, summary="Status: ok, Units connected: 3")
    ]


def test_check_failed() -> None:
    assert list(check_cmctc_state(_section_failed())) == [
        Result(state=State.CRIT, summary="Status: failed, Units connected: 3")
    ]


def test_check_unknown() -> None:
    assert list(check_cmctc_state(_section_unknown())) == [
        Result(state=State.CRIT, summary="Status: unknown[4], Units connected: 1")
    ]
