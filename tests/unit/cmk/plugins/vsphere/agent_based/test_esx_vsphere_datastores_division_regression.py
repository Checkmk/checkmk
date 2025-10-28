#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_datastores as esxds

_STRING_TABLE: Final = [
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


def test_discover_esx_vsphere_datastores_division_regression() -> None:
    """Test discovery function for ESX vSphere datastores."""
    assert list(
        esxds.discover_esx_vsphere_datastores(esxds.parse_esx_vsphere_datastores(_STRING_TABLE))
    ) == [
        Service(item="backup_day_esx_blade_nfs_nfs32"),
        Service(item="datastore01"),
        Service(item="system01_20100701"),
        Service(item="storage_iso"),
    ]


def test_check_esx_vsphere_datastores_division_regression_basic(
    initialised_item_state: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check function basic functionality with value store initialized."""
    monkeypatch.setattr(
        esxds, "get_value_store", lambda: {"system01_20100701.delta": (1761719533.031466, 0)}
    )
    params = {
        "levels": (80.0, 90.0),
        "magic_normsize": 20,
        "levels_low": (50.0, 60.0),
        "trend_range": 24,
        "trend_perfdata": True,
    }

    # Should have at least a filesystem check result
    result = next(
        r
        for r in esxds.check_esx_vsphere_datastores(
            "system01_20100701",
            params,
            esxds.parse_esx_vsphere_datastores(_STRING_TABLE),
        )
        if isinstance(r, Result)
    )

    # First result should be state OK (0) for low usage
    assert result == Result(state=State.OK, summary="Used: 0.21% - 974 MiB of 458 GiB")


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
    parsed = esxds.parse_esx_vsphere_datastores(string_table)
    # Provide basic parameters required for filesystem checks
    params = {"levels": (80.0, 90.0)}
    # Should return multiple results including inaccessible state
    result, *_ = esxds.check_esx_vsphere_datastores("inaccessible_store", params, parsed)

    # First result should be critical state for inaccessible datastore
    assert isinstance(result, Result)
    assert result.state is State.CRIT
    assert "inaccessible" in result.summary.lower()


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
    # Should return empty result for missing datastores
    assert not list(
        esxds.check_esx_vsphere_datastores(
            "missing_store", {}, esxds.parse_esx_vsphere_datastores(string_table)
        )
    )


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
    parsed = esxds.parse_esx_vsphere_datastores(string_table)
    # Zero capacity datastores are not discovered, so no check results expected
    result = list(esxds.check_esx_vsphere_datastores("zero_capacity_store", {}, parsed))

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
    parsed = esxds.parse_esx_vsphere_datastores(string_table)
    # Provide basic parameters required for filesystem checks
    params = {"levels": (80.0, 90.0)}
    result = list(esxds.check_esx_vsphere_datastores("provisioned_store", params, parsed))

    # Should include provisioning information
    assert any("provisioning" in r.summary.lower() for r in result if isinstance(r, Result))

    # Should have overprovisioned metric - check results with at least 3 elements
    metrics = [r for r in result if isinstance(r, Metric)]
    assert any(m.name == "overprovisioned" for m in metrics)


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
    result = esxds.parse_esx_vsphere_datastores(string_table)
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

    result = esxds.parse_esx_vsphere_datastores(string_table)
    assert "minimal_store" in result
    # Should handle missing uncommitted field gracefully
    assert result["minimal_store"]["accessible"] is True
    assert result["minimal_store"]["capacity"] == 1073741824
    assert result["minimal_store"]["freeSpace"] == 536870912
