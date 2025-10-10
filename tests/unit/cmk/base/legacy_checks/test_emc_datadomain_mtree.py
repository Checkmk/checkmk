#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.emc_datadomain_mtree import (
    check_emc_datadomain_mtree,
    discover_emc_datadomain_mtree,
    parse_emc_datadomain_mtree,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["/data/col1/boost_vmware", "3943.3", "3"],
                ["/data/col1/repl_cms_dc1", "33.3", "2"],
                ["/data/col1/nfs_cms_dc1", "0.0", "1"],
                ["something", "0.0", "-1"],
            ],
            [
                ("/data/col1/boost_vmware", {}),
                ("/data/col1/repl_cms_dc1", {}),
                ("/data/col1/nfs_cms_dc1", {}),
                ("something", {}),
            ],
        ),
    ],
)
def test_discover_emc_datadomain_mtree(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for emc_datadomain_mtree check."""
    parsed = parse_emc_datadomain_mtree(string_table)
    result = list(discover_emc_datadomain_mtree(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "/data/col1/boost_vmware",
            {
                "deleted": 2,
                "read-only": 1,
                "read-write": 0,
                "replication destination": 0,
                "retention lock disabled": 0,
                "retention lock enabled": 0,
                "unknown": 3,
            },
            [
                ["/data/col1/boost_vmware", "3943.3", "3"],
                ["/data/col1/repl_cms_dc1", "33.3", "2"],
                ["/data/col1/nfs_cms_dc1", "0.0", "1"],
                ["something", "0.0", "-1"],
            ],
            [(0, "Status: read-write, Precompiled: 3.85 TiB", [("precompiled", 4234086134579)])],
        ),
        (
            "/data/col1/repl_cms_dc1",
            {
                "deleted": 2,
                "read-only": 1,
                "read-write": 0,
                "replication destination": 0,
                "retention lock disabled": 0,
                "retention lock enabled": 0,
                "unknown": 3,
            },
            [
                ["/data/col1/boost_vmware", "3943.3", "3"],
                ["/data/col1/repl_cms_dc1", "33.3", "2"],
                ["/data/col1/nfs_cms_dc1", "0.0", "1"],
                ["something", "0.0", "-1"],
            ],
            [(1, "Status: read-only, Precompiled: 33.3 GiB", [("precompiled", 35755602739)])],
        ),
        (
            "/data/col1/nfs_cms_dc1",
            {
                "deleted": 2,
                "read-only": 1,
                "read-write": 0,
                "replication destination": 0,
                "retention lock disabled": 0,
                "retention lock enabled": 0,
                "unknown": 3,
            },
            [
                ["/data/col1/boost_vmware", "3943.3", "3"],
                ["/data/col1/repl_cms_dc1", "33.3", "2"],
                ["/data/col1/nfs_cms_dc1", "0.0", "1"],
                ["something", "0.0", "-1"],
            ],
            [(2, "Status: deleted, Precompiled: 0 B", [("precompiled", 0)])],
        ),
        (
            "something",
            {
                "deleted": 2,
                "read-only": 1,
                "read-write": 0,
                "replication destination": 0,
                "retention lock disabled": 0,
                "retention lock enabled": 0,
                "unknown": 3,
            },
            [
                ["/data/col1/boost_vmware", "3943.3", "3"],
                ["/data/col1/repl_cms_dc1", "33.3", "2"],
                ["/data/col1/nfs_cms_dc1", "0.0", "1"],
                ["something", "0.0", "-1"],
            ],
            [(3, "Status: invalid code -1, Precompiled: 0 B", [("precompiled", 0)])],
        ),
    ],
)
def test_check_emc_datadomain_mtree(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for emc_datadomain_mtree check."""
    parsed = parse_emc_datadomain_mtree(string_table)
    result = list(check_emc_datadomain_mtree(item, params, parsed))
    assert result == expected_results
