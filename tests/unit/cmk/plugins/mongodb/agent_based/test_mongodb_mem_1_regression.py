#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.mongodb.agent_based.mongodb_mem import (
    check_mongodb_mem,
    discover_mongodb_mem,
    parse_mongodb_mem,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["resident", "856"],
                ["supported", "True"],
                ["virtual", "6100"],
                ["mappedWithJournal", "5374"],
                ["mapped", "2687"],
                ["bits", "64"],
                ["note", "fields", "vary", "by", "platform"],
                ["page_faults", "86"],
                ["heap_usage_bytes", "65501032"],
            ],
            [Service()],
        ),
        (
            [],
            [],
        ),
    ],
)
def test_discover_mongodb_mem_1_regression(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for mongodb_mem regression test."""
    parsed = parse_mongodb_mem(string_table)
    assert list(discover_mongodb_mem(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                ["resident", "856"],
                ["supported", "True"],
                ["virtual", "6100"],
                ["mappedWithJournal", "5374"],
                ["mapped", "2687"],
                ["bits", "64"],
                ["note", "fields", "vary", "by", "platform"],
                ["page_faults", "86"],
                ["heap_usage_bytes", "65501032"],
            ],
            [
                Result(state=State.OK, summary="Resident usage: 856 MiB"),
                Metric("process_resident_size", 897581056.0),
                Result(state=State.OK, summary="Virtual usage: 5.96 GiB"),
                Metric("process_virtual_size", 6396313600.0),
                Result(state=State.OK, summary="Mapped usage: 2.62 GiB"),
                Metric("process_mapped_size", 2817523712.0),
            ],
        ),
    ],
)
def test_check_mongodb_mem_1_regression(
    item: str | None,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Any],
) -> None:
    """Test check function for mongodb_mem regression test."""
    parsed = parse_mongodb_mem(string_table)
    assert list(check_mongodb_mem(params, parsed)) == expected_results
