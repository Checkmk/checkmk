#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import MutableMapping

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.ucd_diskio import (
    _check_ucd_diskio,
    discover_ucd_diskio,
    parse_ucd_diskio,
)


@pytest.fixture(name="string_table")
def snmp_section():
    return [
        [
            ["1", "ram0", "0", "0", "0", "0"],
            ["2", "ram1", "60.0", "120.0", "180.0", "240.0"],
        ]
    ]


def test_discover_ucd_diskio(
    string_table: list[StringTable],
) -> None:
    discovery_results = list(discover_ucd_diskio(parse_ucd_diskio(string_table)))
    assert discovery_results == [
        Service(item="ram0"),
        Service(item="ram1"),
    ]


def test_discover_ucd_diskio_with_empty_section() -> None:
    assert list(discover_ucd_diskio({})) == []


def test_check_ucd_diskio_item_not_found(
    string_table: list[StringTable],
) -> None:
    assert (
        list(
            _check_ucd_diskio(
                item="not_found",
                params={},
                section=parse_ucd_diskio(string_table),
                value_store={},
                this_time=0.0,
            )
        )
        == []
    )


def test_check_ucd_diskio(
    string_table: list[StringTable],
) -> None:
    value_store: MutableMapping = {}

    first_check_result = list(
        _check_ucd_diskio(
            item="ram0",
            params={},
            section=parse_ucd_diskio(string_table),
            value_store=value_store,
            this_time=0.0,
        )
    )

    second_check_result = list(
        _check_ucd_diskio(
            item="ram0",
            params={},
            section=parse_ucd_diskio(string_table),
            value_store=value_store,
            this_time=60.0,
        )
    )

    assert any(isinstance(r, IgnoreResults) for r in first_check_result)

    assert second_check_result == [
        Result(state=State.OK, summary="[1]"),
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=State.OK, summary="Write: 0.00 B/s"),
        Metric("disk_write_throughput", 0.0),
        Result(state=State.OK, notice="Read operations: 0.00/s"),
        Metric("disk_read_ios", 0.0),
        Result(state=State.OK, notice="Write operations: 0.00/s"),
        Metric("disk_write_ios", 0.0),
    ]


def test_check_ucd_diskio_dynamic(
    string_table: list[StringTable],
) -> None:
    value_store: MutableMapping = {
        "ucd_disk_io_read_ios.ram1": (0, 60.0),
        "ucd_disk_io_write_ios.ram1": (0, 60.0),
        "ucd_disk_io_read_throughput.ram1": (0, 60.0),
        "ucd_disk_io_write_throughput.ram1": (0, 60.0),
    }

    check_result = list(
        _check_ucd_diskio(
            item="ram1",
            params={},
            section=parse_ucd_diskio(string_table),
            value_store=value_store,
            this_time=60.0,
        )
    )

    assert check_result == [
        Result(state=State.OK, summary="[2]"),
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=State.OK, summary="Write: 1.00 B/s"),
        Metric("disk_write_throughput", 1.0),
        Result(state=State.OK, notice="Read operations: 2.00/s"),
        Metric("disk_read_ios", 2.0),
        Result(state=State.OK, notice="Write operations: 3.00/s"),
        Metric("disk_write_ios", 3.0),
    ]
