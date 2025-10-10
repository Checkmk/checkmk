#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.hyperv_vmstatus import (
    check_hyperv_vmstatus,
    discover_hyperv_vmstatus,
    parse_hyperv_vmstatus,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["Integration_Services", "Protocol_Mismatch"], ["Replica_Health", "None"]], [(None, {})]),
    ],
)
def test_discover_hyperv_vmstatus(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hyperv_vmstatus check."""
    parsed = parse_hyperv_vmstatus(string_table)
    result = list(discover_hyperv_vmstatus(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [["Integration_Services", "Protocol_Mismatch"], ["Replica_Health", "None"]],
            [0, "Integration Service State: Protocol_Mismatch"],
        ),
    ],
)
def test_check_hyperv_vmstatus(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hyperv_vmstatus check."""
    parsed = parse_hyperv_vmstatus(string_table)
    result = list(check_hyperv_vmstatus(item, params, parsed))
    assert result == expected_results
