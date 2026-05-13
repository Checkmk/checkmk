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
from cmk.legacy_checks.checkpoint_packets import (
    check_checkpoint_packets,
    discover_checkpoint_packets,
    parse_checkpoint_packets,
)


@pytest.fixture(name="string_table_missing_encryption")
def string_table_missing_encryption_fixture() -> list[list[list[str]]]:
    return [
        [["120", "180", "210", "4"]],
        [],
    ]


@pytest.fixture(name="parsed_missing_encryption")
def parsed_missing_encryption_fixture(
    string_table_missing_encryption: list[list[list[str]]],
) -> Mapping[str, int]:
    return parse_checkpoint_packets(string_table_missing_encryption)


def test_parse_checkpoint_packets_missing_encryption(
    string_table_missing_encryption: list[list[list[str]]],
) -> None:
    assert parse_checkpoint_packets(string_table_missing_encryption) == {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
    }


def test_discover_checkpoint_packets_missing_encryption(
    parsed_missing_encryption: Mapping[str, int],
) -> None:
    assert list(discover_checkpoint_packets(parsed_missing_encryption)) == [Service()]


@time_machine.travel("2019-10-28 08:51:18")
def test_check_checkpoint_packets_missing_encryption_initial_run(
    parsed_missing_encryption: Mapping[str, int],
) -> None:
    params = {
        "accepted": (100000, 200000),
        "rejected": (100000, 200000),
        "dropped": (100000, 200000),
        "logged": (100000, 200000),
        "espencrypted": (100000, 200000),
        "espdecrypted": (100000, 200000),
    }
    with pytest.raises(Exception):
        list(check_checkpoint_packets(params, parsed_missing_encryption))


def test_check_checkpoint_packets_missing_encryption_only_basic_metrics() -> None:
    test_data = {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
    }
    assert list(discover_checkpoint_packets(test_data)) == [Service()]


def test_parse_checkpoint_packets_completely_empty_encryption() -> None:
    assert parse_checkpoint_packets(
        [
            [["120", "180", "210", "4"]],
            [],
        ]
    ) == {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
    }


def test_parse_checkpoint_packets_malformed_encryption_data() -> None:
    assert parse_checkpoint_packets(
        [
            [["120", "180", "210", "4"]],
            [["invalid"]],
        ]
    ) == {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
    }


def test_parse_checkpoint_packets_partial_basic_data() -> None:
    assert parse_checkpoint_packets(
        [
            [["120", "180"]],
            [["0", "60"]],
        ]
    ) == {
        "Accepted": 120,
        "Rejected": 180,
        "EspEncrypted": 0,
        "EspDecrypted": 60,
    }
