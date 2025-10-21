#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Unit tests for esx_vsphere_datastores division regression scenarios - Pattern 5."""

from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.esx_vsphere_datastores import (
    check_esx_vsphere_datastores,
    discover_esx_vsphere_datastores,
    parse_esx_vsphere_datastores,
)


@pytest.fixture(name="esx_vsphere_datastores_division_regression_string_table")
def _esx_vsphere_datastores_division_regression_string_table() -> StringTable:
    """ESX vSphere datastores data for division regression test."""
    return [
        ["[backup_day_esx_blade_nfs_nfs32]"],
        ["accessible", "true"],
        ["capacity", "19923665018880"],
        ["freeSpace", "15224133410816"],
        ["type", "NFS"],
        ["uncommitted", "0"],
        ["[datastore01]"],
        ["accessible", "true"],
        ["capacity", "1073741824000"],
        ["freeSpace", "322122547200"],
        ["type", "VMFS"],
        ["uncommitted", "0"],
        ["[system01_20100701]"],
        ["accessible", "true"],
        ["capacity", "492042190848"],
        ["freeSpace", "491020877824"],
        ["type", "VMFS"],
        ["uncommitted", "0"],
        ["[storage_iso]"],
        ["accessible", "true"],
        ["capacity", "7511204864"],
        ["freeSpace", "506974208"],
        ["type", "VMFS"],
        ["uncommitted", "43216809984"],
    ]


@pytest.fixture(name="esx_vsphere_datastores_division_regression_parsed")
def _esx_vsphere_datastores_division_regression_parsed(
    esx_vsphere_datastores_division_regression_string_table: StringTable,
) -> dict[str, dict[str, Any]]:
    """Parsed ESX vSphere datastores data."""
    return parse_esx_vsphere_datastores(esx_vsphere_datastores_division_regression_string_table)


def test_discover_esx_vsphere_datastores_division_regression(
    esx_vsphere_datastores_division_regression_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test discovery function for ESX vSphere datastores."""
    result = list(
        discover_esx_vsphere_datastores(esx_vsphere_datastores_division_regression_parsed)
    )
    # Discovery should include accessible datastores (note: order may vary)
    discovered_items = sorted([item for item, _ in result])
    expected_items = [
        "backup_day_esx_blade_nfs_nfs32",
        "datastore01",
        "storage_iso",
        "system01_20100701",
    ]
    assert discovered_items == sorted(expected_items)


def test_check_esx_vsphere_datastores_division_regression_basic(
    esx_vsphere_datastores_division_regression_parsed: dict[str, dict[str, Any]],
    initialised_item_state: None,
) -> None:
    """Test check function basic functionality with value store initialized."""
    params = {
        "levels": (80.0, 90.0),
        "magic_normsize": 20,
        "levels_low": (50.0, 60.0),
        "trend_range": 24,
        "trend_perfdata": True,
    }

    result = list(
        check_esx_vsphere_datastores(
            "system01_20100701",
            params,
            esx_vsphere_datastores_division_regression_parsed,
        )
    )

    # Should have at least a filesystem check result
    assert len(result) >= 1
    # First result should be state OK (0) for low usage
    assert result[0][0] == 0


def test_check_esx_vsphere_datastores_division_regression_inaccessible(
    initialised_item_state: None,
) -> None:
    """Test check function with inaccessible datastore."""
    string_table = [
        ["[inaccessible_store]"],
        ["accessible", "false"],
        ["capacity", "1000000000"],
        ["freeSpace", "500000000"],
        ["type", "VMFS"],
        ["uncommitted", "0"],
    ]
    parsed = parse_esx_vsphere_datastores(string_table)
    # Provide basic parameters required for filesystem checks
    params = {"levels": (80.0, 90.0)}
    result = list(check_esx_vsphere_datastores("inaccessible_store", params, parsed))

    # Should return multiple results including inaccessible state
    assert len(result) >= 1
    # First result should be critical state for inaccessible datastore
    assert result[0][0] == 2  # Critical state
    assert "inaccessible" in result[0][1].lower()


def test_check_esx_vsphere_datastores_division_regression_missing_data() -> None:
    """Test check function with missing datastore."""
    string_table = [
        ["[present_store]"],
        ["accessible", "true"],
        ["capacity", "1000000000"],
        ["freeSpace", "500000000"],
        ["type", "VMFS"],
        ["uncommitted", "0"],
    ]
    parsed = parse_esx_vsphere_datastores(string_table)
    result = list(check_esx_vsphere_datastores("missing_store", {}, parsed))

    # Should return empty result for missing datastores
    assert len(result) == 0


def test_check_esx_vsphere_datastores_division_regression_zero_capacity(
    initialised_item_state: None,
) -> None:
    """Test check function with zero capacity (division by zero protection)."""
    string_table = [
        ["[zero_capacity_store]"],
        ["accessible", "true"],
        ["capacity", "0"],
        ["freeSpace", "0"],
        ["type", "VMFS"],
        ["uncommitted", "0"],
    ]
    parsed = parse_esx_vsphere_datastores(string_table)
    # Zero capacity datastores are not discovered, so no check results expected
    result = list(check_esx_vsphere_datastores("zero_capacity_store", {}, parsed))

    # Zero capacity datastores should return empty results (no check performed)
    assert len(result) == 0


def test_check_esx_vsphere_datastores_division_regression_provisioning(
    initialised_item_state: None,
) -> None:
    """Test provisioning calculations without division errors."""
    string_table = [
        ["[provisioned_store]"],
        ["accessible", "true"],
        ["capacity", "10737418240"],  # 10 GB
        ["freeSpace", "1073741824"],  # 1 GB
        ["type", "VMFS"],
        ["uncommitted", "5368709120"],  # 5 GB uncommitted
    ]
    parsed = parse_esx_vsphere_datastores(string_table)
    # Provide basic parameters required for filesystem checks
    params = {"levels": (80.0, 90.0)}
    result = list(check_esx_vsphere_datastores("provisioned_store", params, parsed))

    # Should include provisioning information
    provisioning_results = [r for r in result if "provisioning" in r[1].lower()]
    assert len(provisioning_results) >= 1

    # Should have overprovisioned metric - check results with at least 3 elements
    metric_results = [
        r
        for r in result
        if len(r) >= 3 and r[2] and any("overprovisioned" in str(metric) for metric in r[2])
    ]
    assert len(metric_results) >= 1


def test_parse_esx_vsphere_datastores_division_regression_valid_values() -> None:
    """Test parsing with valid integer values."""
    string_table = [
        ["[test_store]"],
        ["accessible", "true"],
        ["capacity", "1000000"],
        ["freeSpace", "500000"],
        ["type", "VMFS"],
        ["uncommitted", "100000"],  # Valid uncommitted value
    ]

    # Should parse valid values correctly
    result = parse_esx_vsphere_datastores(string_table)
    assert "test_store" in result
    assert result["test_store"]["accessible"] is True
    assert result["test_store"]["capacity"] == 1000000
    assert result["test_store"]["freeSpace"] == 500000
    assert result["test_store"]["uncommitted"] == 100000


def test_parse_esx_vsphere_datastores_division_regression_missing_uncommitted() -> None:
    """Test parsing with missing uncommitted field."""
    string_table = [
        ["[minimal_store]"],
        ["accessible", "true"],
        ["capacity", "1073741824"],
        ["freeSpace", "536870912"],
        ["type", "VMFS"],
        # No uncommitted field
    ]

    result = parse_esx_vsphere_datastores(string_table)
    assert "minimal_store" in result
    # Should handle missing uncommitted field gracefully
    assert result["minimal_store"]["accessible"] is True
    assert result["minimal_store"]["capacity"] == 1073741824
    assert result["minimal_store"]["freeSpace"] == 536870912
