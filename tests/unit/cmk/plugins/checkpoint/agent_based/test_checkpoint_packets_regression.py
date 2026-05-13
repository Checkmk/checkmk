#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest
import time_machine

from cmk.agent_based.v2 import Service
from cmk.plugins.checkpoint.agent_based.checkpoint_packets import (
    check_checkpoint_packets,
    discover_checkpoint_packets,
    parse_checkpoint_packets,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[list[str]]]:
    return [
        [["120", "180", "210", "4"]],
        [["0", "60"]],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[list[str]]]) -> Mapping[str, int]:
    return parse_checkpoint_packets(string_table)


def test_parse_checkpoint_packets(string_table: list[list[list[str]]]) -> None:
    assert parse_checkpoint_packets(string_table) == {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
        "EspEncrypted": 0,
        "EspDecrypted": 60,
    }


def test_parse_checkpoint_packets_incomplete_data() -> None:
    assert parse_checkpoint_packets([[["120", "180"]]]) == {
        "Accepted": 120,
        "Rejected": 180,
    }


def test_parse_checkpoint_packets_invalid_values() -> None:
    assert parse_checkpoint_packets(
        [
            [["abc", "180", "210", "4"]],
            [["0", "xyz"]],
        ]
    ) == {
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
        "EspEncrypted": 0,
    }


def test_discover_checkpoint_packets(parsed: Mapping[str, int]) -> None:
    assert list(discover_checkpoint_packets(parsed)) == [Service()]


def test_discover_checkpoint_packets_empty_data() -> None:
    assert list(discover_checkpoint_packets({})) == []


@time_machine.travel("2019-10-28 08:51:18")
def test_check_checkpoint_packets_initial_run(parsed: Mapping[str, int]) -> None:
    params = {
        "accepted": (100000, 200000),
        "rejected": (100000, 200000),
        "dropped": (100000, 200000),
        "logged": (100000, 200000),
        "espencrypted": (100000, 200000),
        "espdecrypted": (100000, 200000),
    }

    with pytest.raises(Exception):
        list(check_checkpoint_packets(params, parsed))


def test_check_checkpoint_packets_empty_parsed() -> None:
    assert list(check_checkpoint_packets({}, {})) == []
