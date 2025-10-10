#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.dell_compellent_controller import (
    check_dell_compellent_controller,
    parse_dell_compellent_controller,
)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {},
            [
                ["1", "1", "Foo", "1.2.3.4", "Model"],
                ["2", "999", "Bar", "5.6.7.8", "Model"],
                ["10", "2", "Baz", "1.3.5.7", "Model"],
            ],
            [(0, "Status: UP"), (0, "Model: Model, Name: Foo, Address: 1.2.3.4")],
        ),
        (
            "2",
            {},
            [
                ["1", "1", "Foo", "1.2.3.4", "Model"],
                ["2", "999", "Bar", "5.6.7.8", "Model"],
                ["10", "2", "Baz", "1.3.5.7", "Model"],
            ],
            [(3, "Status: unknown[999]"), (0, "Model: Model, Name: Bar, Address: 5.6.7.8")],
        ),
        (
            "10",
            {},
            [
                ["1", "1", "Foo", "1.2.3.4", "Model"],
                ["2", "999", "Bar", "5.6.7.8", "Model"],
                ["10", "2", "Baz", "1.3.5.7", "Model"],
            ],
            [(2, "Status: DOWN"), (0, "Model: Model, Name: Baz, Address: 1.3.5.7")],
        ),
    ],
)
def test_check_dell_compellent_controller(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for dell_compellent_controller check."""
    parsed = parse_dell_compellent_controller(string_table)
    result = list(check_dell_compellent_controller(item, params, parsed))
    assert result == expected_results
