#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.hyperv.agent_based.hyperv_vmstatus import (
    check_hyperv_vmstatus,
    discover_hyperv_vmstatus,
    parse_hyperv_vmstatus,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["Integration_Services", "Protocol_Mismatch"], ["Replica_Health", "None"]], [Service()]),
    ],
)
def test_discover_hyperv_vmstatus(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for hyperv_vmstatus check."""
    parsed = parse_hyperv_vmstatus(string_table)
    result = list(discover_hyperv_vmstatus(parsed))
    assert sorted(result, key=lambda x: x.item or "") == sorted(
        expected_discoveries, key=lambda x: x.item or ""
    )


@pytest.mark.parametrize(
    "string_table, expected_results",
    [
        (
            [["Integration_Services", "Protocol_Mismatch"], ["Replica_Health", "None"]],
            [Result(state=State.OK, summary="Integration Service State: Protocol_Mismatch")],
        ),
    ],
)
def test_check_hyperv_vmstatus(
    string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    """Test check function for hyperv_vmstatus check."""
    parsed = parse_hyperv_vmstatus(string_table)
    result = list(check_hyperv_vmstatus(parsed))
    assert result == expected_results
