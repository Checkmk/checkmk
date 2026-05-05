#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.rstcli import (
    check_rstcli,
    check_rstcli_pdisks,
    discover_rstcli,
    discover_rstcli_pdisks,
    parse_rstcli,
)


@pytest.mark.parametrize(
    "string_table",
    [
        [["rstcli not found"]],
    ],
)
def test_discover_rstcli_regression(string_table: StringTable) -> None:
    """Test discovery function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    assert list(discover_rstcli(parsed)) == []


@pytest.mark.parametrize(
    "string_table",
    [
        [["rstcli not found"]],
    ],
)
def test_discover_rstcli_pdisks_regression(string_table: StringTable) -> None:
    """Test pdisks discovery function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    assert list(discover_rstcli_pdisks(parsed)) == []


@pytest.mark.parametrize(
    "item, string_table",
    [
        ("nonexistent_volume", [["rstcli not found"]]),
    ],
)
def test_check_rstcli_regression(item: str, string_table: StringTable) -> None:
    """Test check function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    assert list(check_rstcli(item, parsed)) == []


@pytest.mark.parametrize(
    "item, string_table",
    [
        ("nonexistent/disk", [["rstcli not found"]]),
    ],
)
def test_check_rstcli_pdisks_regression(item: str, string_table: StringTable) -> None:
    """Test pdisks check function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    assert list(check_rstcli_pdisks(item, parsed)) == []
