#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.mongodb_mem import (
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
            [(None, {})],
        ),
    ],
)
def test_discover_mongodb_mem(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mongodb_mem check."""
    parsed = parse_mongodb_mem(string_table)
    result = list(discover_mongodb_mem(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
                (0, "Resident usage: 856 MiB", [("process_resident_size", 897581056, None, None)]),
                (0, "Virtual usage: 5.96 GiB", [("process_virtual_size", 6396313600, None, None)]),
                (0, "Mapped usage: 2.62 GiB", [("process_mapped_size", 2817523712, None, None)]),
            ],
        ),
    ],
)
def test_check_mongodb_mem(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for mongodb_mem check."""
    parsed = parse_mongodb_mem(string_table)
    result = list(check_mongodb_mem(item, params, parsed))
    assert result == expected_results
