#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.apc_mod_pdu_modules import (
    check_apc_mod_pdu_modules,
    inventory_apc_mod_pdu_modules,
    parse_apc_mod_pdu_modules,
)


def _section() -> StringTable:
    return parse_apc_mod_pdu_modules(
        [
            ["Circuit 1a", "1", "12"],
            ["Circuit 1b", "1", "13"],
            ["Circuit 1c", "1", "8"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["Circuit 3a", "1", "22"],
            ["Circuit 3b", "1", "6"],
            ["Circuit 3c", "1", "0"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
            ["", "-1", "-1"],
        ]
    )


def test_discover_apc_mod_pdu_modules() -> None:
    assert list(inventory_apc_mod_pdu_modules(_section())) == [
        Service(item="Circuit 1a"),
        Service(item="Circuit 1b"),
        Service(item="Circuit 1c"),
        Service(item="Circuit 3a"),
        Service(item="Circuit 3b"),
        Service(item="Circuit 3c"),
    ]


def test_discover_apc_mod_pdu_modules_no_items() -> None:
    assert not list(inventory_apc_mod_pdu_modules(parse_apc_mod_pdu_modules([])))


def test_check_apc_mod_pdu_modules() -> None:
    assert list(check_apc_mod_pdu_modules("Circuit 1a", _section())) == [
        Metric("power", 1200.0),
        Result(state=State.OK, summary="Status normal, current: 1.20 kW"),
    ]


def test_check_apc_mod_pdu_modules_vanished_item() -> None:
    assert not list(check_apc_mod_pdu_modules("Not there", _section()))
