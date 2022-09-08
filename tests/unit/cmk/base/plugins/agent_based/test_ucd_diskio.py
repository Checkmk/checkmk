#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import pytest

import cmk.base.plugins.agent_based.ucd_diskio as ucd_diskio
from cmk.base import item_state
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.api.agent_based.utils import GetRateError
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.ucd_diskio import (
    check_ucd_diskio,
    discover_ucd_diskio,
    parse_ucd_diskio,
)


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch) -> None:  # type:ignore[no-untyped-def]
    value_store_patched = {
        "ram0": (1662713424.1758733, 0.0),
    }
    monkeypatch.setattr(ucd_diskio, "get_value_store", lambda: value_store_patched)


@pytest.fixture(name="string_table")
def snmp_section():
    return [
        [
            ["1", "ram0", "0", "0", "0", "0"],
            ["2", "ram1", "0", "0", "0", "0"],
        ]
    ]


def test_discover_ucd_diskio(
    string_table: List[StringTable],
) -> None:
    discovery_results = list(discover_ucd_diskio(parse_ucd_diskio(string_table)))
    assert discovery_results == [
        Service(item="ram0"),
        Service(item="ram1"),
    ]


def test_discover_ucd_diskio_with_empty_section() -> None:
    assert list(discover_ucd_diskio({})) == []


def test_check_ucd_diskio_item_not_found(
    string_table: List[StringTable],
) -> None:
    assert (
        list(
            check_ucd_diskio(
                item="not_found",
                params={},
                section=parse_ucd_diskio(string_table),
            )
        )
        == []
    )


def test_check_ucd_diskio_raise_get_rate_error(
    string_table: List[StringTable],
) -> None:
    with pytest.raises(GetRateError):
        list(
            check_ucd_diskio(
                item="ram0",
                params={},
                section=parse_ucd_diskio(string_table),
            )
        )


def test_check_ucd_diskio(
    string_table: List[StringTable],
    value_store_patch: None,
) -> None:
    for field in ["read_ios", "write_ios", "read_throughput", "write_throughput"]:
        # Setting the previous states, so that the get_rate function doesn't return a GetRateError
        item_state.set_item_state(f"ucd_disk_io_{field}.ram0", (0, 0))

    check_result = list(
        check_ucd_diskio(
            item="ram0",
            params={},
            section=parse_ucd_diskio(string_table),
        )
    )

    assert len(check_result) == 9  # The first result plus a Result and Metric for every field
    assert check_result[0] == Result(state=State.OK, summary="[1]")
    assert check_result[1:] == [
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=State.OK, summary="Write: 0.00 B/s"),
        Metric("disk_write_throughput", 0.0),
        Result(state=State.OK, notice="Read operations: 0.00/s"),
        Metric("disk_read_ios", 0.0),
        Result(state=State.OK, notice="Write operations: 0.00/s"),
        Metric("disk_write_ios", 0.0),
    ]
