#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.emc_isilon_ifs import (
    check_emc_isilon_ifs,
    discover_emc_isilon_ifs,
)
from cmk.plugins.collection.agent_based.emc_isilon_ifs import parse_emc_isilon_ifs
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_LEVELS


@pytest.fixture(name="emc_isilon_ifs_regression_data")
def _emc_isilon_ifs_regression_data() -> StringTable:
    """Return test data from regression dataset."""
    return [["615553001652224", "599743491129344"]]


class TestEmcIsilonIfsRegression:
    """Test EMC Isilon IFS filesystem check with regression dataset."""

    def test_parse_function(self, emc_isilon_ifs_regression_data: StringTable) -> None:
        """Test parse function for EMC Isilon IFS."""
        result = parse_emc_isilon_ifs(emc_isilon_ifs_regression_data)
        # Parse returns FSBlock tuple: (name, total_mb, avail_mb, reserved_mb)
        assert result == ("ifs", 587037088, 571959963, 0)

    def test_discovery_cluster(self, emc_isilon_ifs_regression_data: StringTable) -> None:
        """Test discovery function finds cluster filesystem."""
        parsed = parse_emc_isilon_ifs(emc_isilon_ifs_regression_data)
        assert parsed is not None
        result = list(discover_emc_isilon_ifs(parsed))
        # Always discovers "Cluster" filesystem
        assert result == [("Cluster", None)]

    def test_check_function_cluster_filesystem(
        self, emc_isilon_ifs_regression_data: StringTable
    ) -> None:
        """Test check function for cluster filesystem usage."""
        parsed = parse_emc_isilon_ifs(emc_isilon_ifs_regression_data)
        assert parsed is not None
        result = list(check_emc_isilon_ifs("Cluster", FILESYSTEM_DEFAULT_LEVELS, parsed))

        # Should return [state, message, perfdata]
        assert len(result) == 3
        state, message, perfdata = result

        # State should be OK (0)
        assert state == 0

        # Message should contain usage information
        assert "Used: 2.57%" in message
        assert "14.4 TiB of 560 TiB" in message

        # Performance data should contain expected metrics
        expected_perfdata = [
            ("fs_used", 15077125, 469629670.4, 528333379.2, 0, 587037088.0),
            ("fs_free", 571959963, None, None, 0, None),
            ("fs_used_percent", 2.5683428369691015, 80.0, 90.0, 0.0, 100.0),
            ("fs_size", 587037088, None, None, 0, None),
        ]
        # Check performance data approximately since there are floating point precision differences
        assert len(perfdata) == len(expected_perfdata)
        for actual, expected in zip(perfdata, expected_perfdata):
            assert actual[0] == expected[0]  # metric name
            if isinstance(actual[1], float) and isinstance(expected[1], int | float):
                assert abs(actual[1] - expected[1]) < 1  # value (allow small differences)
            else:
                assert actual[1] == expected[1]

    def test_check_function_nonexistent_item(
        self, emc_isilon_ifs_regression_data: StringTable
    ) -> None:
        """Test check function with non-existent filesystem item."""
        parsed = parse_emc_isilon_ifs(emc_isilon_ifs_regression_data)
        assert parsed is not None
        result = list(check_emc_isilon_ifs("NonExistent", FILESYSTEM_DEFAULT_LEVELS, parsed))
        # The df_check_filesystem_list function still returns results even for non-matching items
        # since it processes the filesystem data provided
        assert len(result) == 3
        assert isinstance(result[0], int)  # state
        assert isinstance(result[1], str)  # message
        assert isinstance(result[2], list)  # perfdata


@pytest.mark.parametrize(
    "test_data, expected_parsed",
    [
        # Regression data
        ([["615553001652224", "599743491129344"]], ("ifs", 587037088, 571959963, 0)),
        # Different filesystem sizes
        ([["1073741824000", "536870912000"]], ("ifs", 1024000, 512000, 0)),
        # Nearly full filesystem
        ([["107374182400", "1073741824"]], ("ifs", 102400, 1024, 0)),
    ],
)
def test_emc_isilon_ifs_parse_scenarios(
    test_data: StringTable, expected_parsed: tuple[str, int, int, int]
) -> None:
    """Test parse function with various filesystem scenarios."""
    result = parse_emc_isilon_ifs(test_data)
    assert result == expected_parsed


@pytest.mark.parametrize(
    "total_bytes, avail_bytes, expected_usage_percent",
    [
        # Regression case: 2.57% usage
        (615553001652224, 599743491129344, 2.5683428369691015),
        # 50% usage
        (1073741824000, 536870912000, 50.0),
        # 90% usage (critical threshold)
        (1073741824000, 107374182400, 90.0),
        # 95% usage
        (1073741824000, 53687091200, 95.0),
    ],
)
def test_emc_isilon_ifs_usage_calculation(
    total_bytes: int, avail_bytes: int, expected_usage_percent: float
) -> None:
    """Test filesystem usage percentage calculation."""
    test_data = [[str(total_bytes), str(avail_bytes)]]
    parsed = parse_emc_isilon_ifs(test_data)
    assert parsed is not None

    result = list(check_emc_isilon_ifs("Cluster", FILESYSTEM_DEFAULT_LEVELS, parsed))
    assert len(result) == 3
    _, _, perfdata = result

    # Check usage percentage in performance data
    fs_used_percent = next(metric for metric in perfdata if metric[0] == "fs_used_percent")
    assert abs(fs_used_percent[1] - expected_usage_percent) < 0.01


def test_emc_isilon_ifs_custom_thresholds() -> None:
    """Test check function with custom warning/critical thresholds."""
    test_data = [["1073741824000", "107374182400"]]  # 90% usage
    parsed = parse_emc_isilon_ifs(test_data)
    assert parsed is not None

    # Custom thresholds: warn at 85%, crit at 95%
    custom_params = {"levels": (85.0, 95.0)}
    result = list(check_emc_isilon_ifs("Cluster", custom_params, parsed))

    assert len(result) == 3
    state, message, _ = result

    # Should be warning (1) since 90% > 85%
    assert state == 1
    assert "warn/crit at 85.00%/95.00%" in message


def test_emc_isilon_ifs_critical_threshold() -> None:
    """Test check function with filesystem at critical threshold."""
    test_data = [["1073741824000", "53687091200"]]  # 95% usage
    parsed = parse_emc_isilon_ifs(test_data)
    assert parsed is not None

    result = list(check_emc_isilon_ifs("Cluster", FILESYSTEM_DEFAULT_LEVELS, parsed))

    assert len(result) == 3
    state, message, _ = result

    # Should be critical (2) since 95% > 90%
    assert state == 2
    assert "warn/crit at 80.00%/90.00%" in message


def test_emc_isilon_ifs_empty_data() -> None:
    """Test parse function with empty data."""
    result = parse_emc_isilon_ifs([])
    assert result is None


def test_emc_isilon_ifs_discovery_with_none() -> None:
    """Test discovery function when parse returns None."""
    # The inventory function actually returns Cluster even with None input
    # This is how it's implemented - it always returns Cluster
    result = list(discover_emc_isilon_ifs(None))  # type: ignore[arg-type]
    assert result == [("Cluster", None)]


def test_emc_isilon_ifs_bytes_conversion() -> None:
    """Test that bytes are correctly converted to MiB in parse function."""
    # 1 GiB in bytes = 1073741824
    # 1 GiB in MiB = 1024
    test_data = [["1073741824", "536870912"]]  # 1 GiB total, 512 MiB available
    parsed = parse_emc_isilon_ifs(test_data)
    assert parsed is not None

    name, total_mb, avail_mb, reserved_mb = parsed
    assert name == "ifs"
    assert total_mb == 1024  # 1073741824 / (1024*1024)
    assert avail_mb == 512  # 536870912 / (1024*1024)
    assert reserved_mb == 0


def test_emc_isilon_ifs_performance_data_format() -> None:
    """Test that performance data follows expected format."""
    test_data = [["1073741824000", "536870912000"]]  # 1 TB total, 500 GB available
    parsed = parse_emc_isilon_ifs(test_data)
    assert parsed is not None

    result = list(check_emc_isilon_ifs("Cluster", FILESYSTEM_DEFAULT_LEVELS, parsed))
    assert len(result) == 3
    _, _, perfdata = result

    # Verify all required metrics are present
    metric_names = [metric[0] for metric in perfdata]
    expected_metrics = ["fs_used", "fs_free", "fs_used_percent", "fs_size"]
    for expected_metric in expected_metrics:
        assert expected_metric in metric_names

    # Verify fs_used_percent has correct thresholds
    fs_used_percent = next(metric for metric in perfdata if metric[0] == "fs_used_percent")
    assert fs_used_percent[2] == 80.0  # warning threshold
    assert fs_used_percent[3] == 90.0  # critical threshold
    assert fs_used_percent[4] == 0.0  # min value
    assert fs_used_percent[5] == 100.0  # max value
