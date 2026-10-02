#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.bi._autocompleters import matching_aggregation_groups

GROUPS = [("Hosts", "Hosts"), ("Hosts/Linux", "Hosts/Linux"), ("Network", "Network")]


@pytest.mark.parametrize(
    "value, strict, expected",
    [
        ("", False, ["Hosts", "Hosts/Linux", "Network"]),
        ("host", False, ["host", "Hosts", "Hosts/Linux"]),
        ("Hosts", False, ["Hosts", "Hosts/Linux"]),
        ("UNKNOWN", False, ["UNKNOWN"]),
        ("UNKNOWN", True, []),
    ],
)
def test_matching_aggregation_groups(value: str, strict: bool, expected: list[str]) -> None:
    assert [
        ident for ident, _title in matching_aggregation_groups(GROUPS, value, strict=strict)
    ] == expected
