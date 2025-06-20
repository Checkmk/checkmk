#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based import if64
from cmk.plugins.lib import interfaces


def test_parse_if64adm() -> None:
    assert if64.parse_if64adm(
        [
            ["1", "1"],
            ["2", ""],
            ["3", "2"],
        ]
    ) == {
        "1": "1",
        "3": "2",
    }


def test_add_admin_status_to_ifaces() -> None:
    ifaces = [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="1",
                descr="GigabitEthernet1/1",
                alias="** Trunk to main switch **",
                type="6",
            ),
            interfaces.Counters(),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="2",
                descr="Primary Internet connection",
                alias="",
                type="6",
            ),
            interfaces.Counters(),
        ),
    ]
    if64._add_admin_status_to_ifaces(ifaces, {"1": "1"})
    assert ifaces[0].attributes.admin_status == "1"
    assert ifaces[1].attributes.admin_status is None


def test_check_timestamps_decrease() -> None:
    value_store: dict[str, object] = {}
    assert not list(if64._check_timestamps({"a": 1, "b": 2}, value_store))
    assert list(if64._check_timestamps({"a": 0, "b": 1}, value_store)) == [
        Result(
            state=State.OK,
            notice="The uptime has decreased since the last check cycle for these node(s): \nThe device might have rebooted or its uptime counter overflowed.",
        )
    ]


def test_check_timestamps_no_change() -> None:
    value_store: dict[str, object] = {}
    assert not list(if64._check_timestamps({"a": 1, "b": 2}, value_store))
    assert list(if64._check_timestamps({"a": 1, "b": 2}, value_store)) == [
        Result(
            state=State.OK,
            notice="The uptime did not change since the last check cycle for these node(s): a, b\nIt is likely that no new data was collected.",
        )
    ]


def test_check_timestamps_valid() -> None:
    value_store: dict[str, object] = {}
    assert not list(if64._check_timestamps({"a": 1, "b": 2}, value_store))
    assert not list(if64._check_timestamps({"a": 61, "b": 62}, value_store))
