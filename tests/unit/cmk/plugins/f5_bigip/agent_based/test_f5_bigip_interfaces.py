#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping, Sequence

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5_bigip.agent_based.f5_bigip_interfaces import (
    check_f5_bigip_interfaces,
    discover_f5_bigip_interfaces,
    Interface,
    parse_f5_bigip_interfaces,
)

from ..conftest import value_store

# port, state, in bytes, out bytes
_STRING_TABLE: StringTable = [
    ["1.1", "0", "6000", "7000"],
    ["1.2", "1", "0", "0"],
    ["1.3", "2", "0", "0"],
    ["mgmt", "5", "0", "0"],
    ["absent", "", "", ""],
]

# One minute earlier, so port 1.1 yields 50 B/s in and 100 B/s out.
_VALUE_STORE: MutableMapping[str, object] = {"in": (0.0, 3000), "out": (0.0, 1000)}


def test_parse_f5_bigip_interfaces() -> None:
    """A port whose OIDs the device does not answer is skipped, the others are kept."""
    assert parse_f5_bigip_interfaces(_STRING_TABLE) == {
        "1.1": Interface(state=0, inbytes=6000, outbytes=7000),
        "1.2": Interface(state=1, inbytes=0, outbytes=0),
        "1.3": Interface(state=2, inbytes=0, outbytes=0),
        "mgmt": Interface(state=5, inbytes=0, outbytes=0),
    }


def test_discover_f5_bigip_interfaces() -> None:
    """Only interfaces that are up are discovered."""
    assert list(discover_f5_bigip_interfaces(parse_f5_bigip_interfaces(_STRING_TABLE))) == [
        Service(item="1.1")
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_interfaces_up() -> None:
    with value_store(_VALUE_STORE):
        assert list(check_f5_bigip_interfaces("1.1", parse_f5_bigip_interfaces(_STRING_TABLE))) == [
            Result(state=State.OK, summary="Up"),
            Result(state=State.OK, summary="In bytes: 50.0 B/s"),
            Metric("bytes_in", 50.0),
            Result(state=State.OK, summary="Out bytes: 100 B/s"),
            Metric("bytes_out", 100.0),
        ]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            "1.2",
            [Result(state=State.CRIT, summary="Down (has no link and is initialized)")],
            id="down",
        ),
        pytest.param(
            "1.3",
            [Result(state=State.CRIT, summary="Disabled (has been forced down)")],
            id="disabled",
        ),
        pytest.param(
            "mgmt",
            [
                Result(
                    state=State.CRIT,
                    summary="Unpopulated (interface not physically populated)",
                )
            ],
            id="unpopulated",
        ),
    ],
)
@time_machine.travel(60.0)
def test_check_f5_bigip_interfaces_not_up(item: str, expected: Sequence[Result | Metric]) -> None:
    """An interface that is not up reports its state and no traffic."""
    with value_store(_VALUE_STORE):
        assert (
            list(check_f5_bigip_interfaces(item, parse_f5_bigip_interfaces(_STRING_TABLE)))
            == expected
        )


@time_machine.travel(60.0)
def test_check_f5_bigip_interfaces_unknown_state() -> None:
    section = parse_f5_bigip_interfaces([["1.1", "42", "0", "0"]])
    with value_store(_VALUE_STORE):
        assert list(check_f5_bigip_interfaces("1.1", section)) == [
            Result(state=State.UNKNOWN, summary="Unknown state (42)")
        ]


@time_machine.travel(60.0)
def test_check_f5_bigip_interfaces_unknown_item() -> None:
    with value_store(_VALUE_STORE):
        assert (
            list(check_f5_bigip_interfaces("nonexistent", parse_f5_bigip_interfaces(_STRING_TABLE)))
            == []
        )


def test_parse_f5_bigip_interfaces_rejects_a_non_numeric_counter() -> None:
    """A value that is present has to be a number; anything else is a broken MIB."""
    with pytest.raises(ValueError):
        parse_f5_bigip_interfaces([["1.1", "not a state", "0", "0"]])
