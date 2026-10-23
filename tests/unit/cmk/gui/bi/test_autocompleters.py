#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.bi._autocompleters import matching_aggregation_groups


@pytest.mark.parametrize(
    "value, strict, expected_group_ids",
    [
        pytest.param("", False, ["Hosts", "Hosts/Linux", "Network"], id="empty query matches all"),
        pytest.param("hosts", False, ["hosts", "Hosts", "Hosts/Linux"], id="case insensitive"),
        pytest.param("hosts", True, ["Hosts", "Hosts/Linux"], id="case insensitive (strict)"),
        pytest.param("Hosts", False, ["Hosts", "Hosts/Linux"], id="exact match"),
        pytest.param("UNKNOWN", False, ["UNKNOWN"], id="no match"),
        pytest.param("UNKNOWN", True, [], id="no match (strict)"),
    ],
)
def test_matching_aggregation_groups(
    value: str, strict: bool, expected_group_ids: list[str]
) -> None:
    all_groups = [
        ("Hosts", "Hosts"),
        ("Hosts/Linux", "Hosts/Linux"),
        ("Network", "Network"),
    ]
    matching_groups = matching_aggregation_groups(all_groups, value, strict=strict)
    matching_group_ids = [ident for ident, _ in matching_groups]
    assert matching_group_ids == expected_group_ids
