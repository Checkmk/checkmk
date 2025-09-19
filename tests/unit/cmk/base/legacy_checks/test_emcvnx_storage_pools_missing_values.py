#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.emcvnx_storage_pools import (
    check_emcvnx_storage_pools,
    check_emcvnx_storage_pools_deduplication,
    check_emcvnx_storage_pools_tiering,
    check_emcvnx_storage_pools_tieringtypes,
    inventory_emcvnx_storage_pools,
    inventory_emcvnx_storage_pools_tiering,
    inventory_emcvnx_storage_pools_tieringtypes,
    parse_emcvnx_storage_pools,
)


@pytest.fixture(name="emcvnx_storage_pools_missing_values_string_table")
def _emcvnx_storage_pools_missing_values_string_table() -> StringTable:
    """EMC VNX storage pools data with missing values scenario."""
    return [
        ["[[[storage_pools]]]"],
        ["Pool Name", "  fake_pool"],
        ["Pool ID", "  4"],
        ["Raid Type", "  "],
        ["Percent Full Threshold", "  "],
        ["Description", "  "],
        ["Disk Type", "  "],
        ["State", "  Ready"],
        ["Status", "  OK(0x0)"],
        ["Current Operation", "  "],
        ["Current Operation State", "  "],
        ["Current Operation Status", "  "],
        ["Current Operation Percent Completed", "  "],
        ["Raw Capacity (Blocks)", "  "],
        ["Raw Capacity (GBs)", "  "],
        ["User Capacity (Blocks)", "  "],
        ["User Capacity (GBs)", "  100"],
        ["Consumed Capacity (Blocks)", "  "],
        ["Consumed Capacity (GBs)", "  50"],
        ["Available Capacity (Blocks)", "  "],
        ["Available Capacity (GBs)", "  50"],
        ["Percent Full", "  50"],
        ["LUN Allocation (Blocks)", "  "],
        ["LUN Allocation (GBs)", "  "],
        ["Percent Subscribed", "  50"],
        ["Oversubscribed by (Blocks)", "  "],
        ["Oversubscribed by (GBs)", "  0"],
        ["Total Subscribed Capacity (Blocks)", "  "],
        ["Total Subscribed Capacity (GBs)", "  50"],
        ["Snapshot Pool Size (Blocks)", "  "],
        ["Snapshot Pool Size (GBs)", "  "],
        ["Snapshot Allocation (Blocks)", "  "],
        ["Snapshot Allocation (GBs)", "  "],
        ["Used Snapshot Pool Size (Blocks)", "  "],
        ["Used Snapshot Pool Size (GBs)", "  "],
        ["Snapshot Space Used Percent", "  "],
        ["Auto-Delete Snapshot Space Threshold", "  "],
        ["Auto-Delete Snapshot Space Threshold Enabled", "  "],
        ["Auto-Delete Snapshot Space Used Threshold Enabled", "  "],
        ["Auto-Delete Snapshot Space Used High Watermark", "  "],
        ["Auto-Delete Snapshot Space Used Low Watermark", "  "],
        ["Auto-Delete Snapshot Space Used State", "  "],
        [""],
        ["[[[auto_tiering]]]"],
        ["Storage Pool Name", "  fake_pool"],
        ["FAST Cache", "  Enabled"],
        ["Relocation Status", "  Manual"],
        ["Relocation Rate", "  Medium"],
        ["Data to Move Up (GBs)", "  0"],
        ["Data to Move Down (GBs)", "  0"],
        ["Data to Move Within Tiers (GBs)", "  0"],
        ["Data Movement Completed (GBs)", "  100"],
        ["Estimated Time to Complete", "  0 hours, 0 minutes"],
        ["Tier Name", "  FAST_Cache"],
        ["Disk Type", "  Flash 2"],
        ["Capacity (GBs)", "  "],
        ["Free Capacity (GBs)", "  "],
        # Note: FAST_Cache tier has missing values for most fields to test missing value handling
        ["Disks (Type)", "  N/A"],
        ["Tier Name", "  Extreme_Performance"],
        ["Disk Type", "  SAS 3"],
        ["Capacity (GBs)", "  1000"],
        ["Free Capacity (GBs)", "  500"],
        ["Percent Subscribed", "  50%"],
        ["Data Targeted for Higher Tier (GBs)", "  10"],
        ["Data Targeted for Lower Tier (GBs)", "  20"],
        ["Data Targeted for Within Tier (GBs)", "  5"],
        ["Disks (Type)", "  N/A"],
        # Deduplication status information
        ["Deduplication State", "  Enabled"],
        ["Deduplication Status", "  OK(0x0)"],
        ["Deduplication Rate", "  High"],
        ["Efficiency Savings (GBs)", "  250"],
        ["Deduplication Percent Completed", "  85"],
        ["Deduplication Remaining Size (GBs)", "  25"],
        ["Deduplication Shared Capacity (GBs)", "  200"],
    ]


@pytest.fixture(name="emcvnx_storage_pools_missing_values_parsed")
def _emcvnx_storage_pools_missing_values_parsed(
    emcvnx_storage_pools_missing_values_string_table: StringTable,
) -> dict[str, dict[str, Any]]:
    """Parsed EMC VNX storage pools data with missing values."""
    return parse_emcvnx_storage_pools(emcvnx_storage_pools_missing_values_string_table)


def test_inventory_emcvnx_storage_pools_missing_values_general(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test discovery function for EMC VNX storage pools general check with missing values."""
    result = list(inventory_emcvnx_storage_pools(emcvnx_storage_pools_missing_values_parsed))
    assert result == [("fake_pool", {})]


def test_inventory_emcvnx_storage_pools_missing_values_tiering(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test discovery function for EMC VNX storage pools tiering check with missing values."""
    result = list(
        inventory_emcvnx_storage_pools_tiering(emcvnx_storage_pools_missing_values_parsed)
    )
    assert result == [("fake_pool", {})]


def test_inventory_emcvnx_storage_pools_missing_values_tieringtypes(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test discovery function for EMC VNX storage pools tiering types check with missing values."""
    result = list(
        inventory_emcvnx_storage_pools_tieringtypes(emcvnx_storage_pools_missing_values_parsed)
    )
    assert result == [("fake_pool FAST_Cache", {}), ("fake_pool Extreme_Performance", {})]


def test_check_emcvnx_storage_pools_missing_values_general(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test general check function for EMC VNX storage pools with missing values."""
    result = list(
        check_emcvnx_storage_pools(
            "fake_pool",
            {"percent_full": (70.0, 90.0)},
            emcvnx_storage_pools_missing_values_parsed,
        )
    )
    expected = [
        (
            0,
            "State: Ready, Status: OK(0x0), [Phys. capacity] User capacity: 100 GiB, Consumed capacity: 50.0 GiB, Available capacity: 50.0 GiB",
        ),
        (0, "Percent full: 50.00%"),
        (
            0,
            "[Virt. capacity] Percent subscribed: 50.00%, Oversubscribed by: 0 B, Total subscribed capacity: 50.0 GiB",
            [
                ("emcvnx_consumed_capacity", 53687091200.0),
                ("emcvnx_avail_capacity", 53687091200.0),
                ("emcvnx_perc_full", 50.0),
                ("emcvnx_perc_subscribed", 50.0),
                ("emcvnx_over_subscribed", 0.0),
                ("emcvnx_total_subscribed_capacity", 53687091200.0),
            ],
        ),
    ]
    assert result == expected


def test_check_emcvnx_storage_pools_missing_values_general_thresholds(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test general check function with thresholds triggered for EMC VNX storage pools."""
    result = list(
        check_emcvnx_storage_pools(
            "fake_pool",
            {"percent_full": (40.0, 60.0)},  # Lower thresholds to trigger warning
            emcvnx_storage_pools_missing_values_parsed,
        )
    )
    # Check that warning state is triggered
    assert result[1][0] == 1  # Warning state
    assert "warn/crit at" in result[1][1]


def test_check_emcvnx_storage_pools_missing_values_tiering(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test tiering check function for EMC VNX storage pools with missing values."""
    result = list(
        check_emcvnx_storage_pools_tiering(
            "fake_pool",
            {"time_to_complete": (21 * 60 * 60 * 24, 28 * 60 * 60 * 24)},
            emcvnx_storage_pools_missing_values_parsed,
        )
    )
    expected = [
        (0, "Fast cache: Enabled"),
        (0, "Relocation status: Manual"),
        (0, "Relocation rate: Medium"),
        (0, "Move up: 0 B", [("emcvnx_move_up", 0.0, None, None)]),
        (0, "Move down: 0 B", [("emcvnx_move_down", 0.0, None, None)]),
        (0, "Move within: 0 B", [("emcvnx_move_within", 0.0, None, None)]),
        (0, "Movement completed: 100 GiB", [("emcvnx_move_completed", 107374182400.0, None, None)]),
        (0, "Estimated time to complete: 0 hours, 0 minutes"),
        (0, "Age: 0 seconds", [("emcvnx_time_to_complete", 0, 1814400, 2419200)]),
    ]
    assert result == expected


def test_check_emcvnx_storage_pools_missing_values_tieringtypes_fast_cache(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test tiering types check function for FAST_Cache tier with missing values."""
    result = list(
        check_emcvnx_storage_pools_tieringtypes(
            "fake_pool FAST_Cache",
            {},
            emcvnx_storage_pools_missing_values_parsed,
        )
    )
    # FAST_Cache tier has missing capacity values, so no results expected since all fields are empty
    assert len(result) == 0


def test_check_emcvnx_storage_pools_missing_values_tieringtypes_extreme_performance(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test tiering types check function for Extreme_Performance tier with missing values."""
    result = list(
        check_emcvnx_storage_pools_tieringtypes(
            "fake_pool Extreme_Performance",
            {},
            emcvnx_storage_pools_missing_values_parsed,
        )
    )
    # Extreme_Performance tier has complete data: percent subscribed and movement data
    assert len(result) >= 3  # Should have percent subscribed and movement data
    result_text = " ".join([item[1] for item in result])
    # Check for key information that should be present
    assert "Percent subscribed" in result_text
    assert "Move" in result_text


def test_check_emcvnx_storage_pools_missing_values_deduplication(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test deduplication check function for EMC VNX storage pools with missing values."""
    result = list(
        check_emcvnx_storage_pools_deduplication(
            "fake_pool",
            {},
            emcvnx_storage_pools_missing_values_parsed,
        )
    )
    expected = [
        (0, "State: Enabled"),
        (0, "Status: OK"),
        (0, "Rate: High"),
        (0, "Efficiency savings: 250 GiB", [("emcvnx_dedupl_efficiency_savings", 268435456000.0)]),
        (0, "Percent completed: 85.00%", [("emcvnx_dedupl_perc_completed", 85.0)]),
        (0, "Remaining size: 25.0 GiB", [("emcvnx_dedupl_remaining_size", 26843545600.0)]),
        (0, "Shared capacity: 200 GiB", [("emcvnx_dedupl_shared_capacity", 214748364800.0)]),
    ]
    assert result == expected


def test_check_emcvnx_storage_pools_missing_values_nonexistent_item(
    emcvnx_storage_pools_missing_values_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test check functions with nonexistent item return None."""
    result_general = check_emcvnx_storage_pools(
        "nonexistent_pool", {}, emcvnx_storage_pools_missing_values_parsed
    )
    result_tiering = check_emcvnx_storage_pools_tiering(
        "nonexistent_pool", {}, emcvnx_storage_pools_missing_values_parsed
    )
    result_deduplication = check_emcvnx_storage_pools_deduplication(
        "nonexistent_pool", {}, emcvnx_storage_pools_missing_values_parsed
    )

    # Check functions should return None for nonexistent items
    assert result_general is None or list(result_general) == []
    assert result_tiering is None or list(result_tiering) == []
    assert result_deduplication is None or list(result_deduplication) == []
