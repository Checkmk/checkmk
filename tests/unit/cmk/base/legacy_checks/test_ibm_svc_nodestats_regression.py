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

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.ibm_svc_nodestats import (
    check_ibm_svc_nodestats_cache,
    check_ibm_svc_nodestats_cpu,
    check_ibm_svc_nodestats_disk_latency,
    check_ibm_svc_nodestats_diskio,
    check_ibm_svc_nodestats_iops,
    discover_ibm_svc_nodestats_cache,
    discover_ibm_svc_nodestats_cpu,
    discover_ibm_svc_nodestats_disk_latency,
    discover_ibm_svc_nodestats_diskio,
    discover_ibm_svc_nodestats_iops,
    parse_ibm_svc_nodestats,
)


@pytest.fixture(name="parsed")
def _parsed() -> Mapping[str, Any]:
    """
    IBM SVC node stats data with multiple services: disk I/O, IOPS, latency, CPU, and cache.
    Provides metrics for VDisks, MDisks, and Drives per node.
    """
    string_table = [
        ["1", "BLUBBSVC01", "compression_cpu_pc", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "cpu_pc", "1", "3", "140325134526"],
        ["1", "BLUBBSVC01", "fc_mb", "35", "530", "140325134526"],
        ["1", "BLUBBSVC01", "fc_io", "5985", "11194", "140325134751"],
        ["1", "BLUBBSVC01", "sas_mb", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "sas_io", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "iscsi_mb", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "iscsi_io", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "write_cache_pc", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "total_cache_pc", "70", "77", "140325134716"],
        ["1", "BLUBBSVC01", "vdisk_mb", "1", "246", "140325134526"],
        ["1", "BLUBBSVC01", "vdisk_io", "130", "1219", "140325134501"],
        ["1", "BLUBBSVC01", "vdisk_ms", "0", "4", "140325134531"],
        ["1", "BLUBBSVC01", "mdisk_mb", "17", "274", "140325134526"],
        ["1", "BLUBBSVC01", "mdisk_io", "880", "1969", "140325134526"],
        ["1", "BLUBBSVC01", "mdisk_ms", "1", "5", "140325134811"],
        ["1", "BLUBBSVC01", "drive_mb", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_io", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_ms", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "vdisk_r_mb", "0", "244", "140325134526"],
        ["1", "BLUBBSVC01", "vdisk_r_io", "19", "1022", "140325134501"],
        ["1", "BLUBBSVC01", "vdisk_r_ms", "2", "8", "140325134756"],
        ["1", "BLUBBSVC01", "vdisk_w_mb", "0", "2", "140325134701"],
        ["1", "BLUBBSVC01", "vdisk_w_io", "110", "210", "140325134901"],
        ["1", "BLUBBSVC01", "vdisk_w_ms", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "mdisk_r_mb", "1", "265", "140325134526"],
        ["1", "BLUBBSVC01", "mdisk_r_io", "15", "1081", "140325134526"],
        ["1", "BLUBBSVC01", "mdisk_r_ms", "5", "23", "140325134616"],
        ["1", "BLUBBSVC01", "mdisk_w_mb", "16", "132", "140325134751"],
        ["1", "BLUBBSVC01", "mdisk_w_io", "865", "1662", "140325134736"],
        ["1", "BLUBBSVC01", "mdisk_w_ms", "1", "5", "140325134811"],
        ["1", "BLUBBSVC01", "drive_r_mb", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_r_io", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_r_ms", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_w_mb", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_w_io", "0", "0", "140325134931"],
        ["1", "BLUBBSVC01", "drive_w_ms", "0", "0", "140325134931"],
        ["5", "BLUBBSVC02", "compression_cpu_pc", "0", "0", "140325134930"],
        ["5", "BLUBBSVC02", "cpu_pc", "1", "2", "140325134905"],
        ["5", "BLUBBSVC02", "fc_mb", "141", "293", "140325134755"],
        ["5", "BLUBBSVC02", "fc_io", "7469", "12230", "140325134750"],
        ["5", "BLUBBSVC02", "sas_mb", "0", "0", "140325134930"],
        ["5", "BLUBBSVC02", "sas_io", "0", "0", "140325134930"],
    ]
    return parse_ibm_svc_nodestats(string_table)


def test_parse_ibm_svc_nodestats(parsed: Mapping[str, Any]) -> None:
    """Test parsing of IBM SVC node stats data."""
    assert (
        len(parsed) == 5
    )  # BLUBBSVC01, VDisks BLUBBSVC01, MDisks BLUBBSVC01, Drives BLUBBSVC01, BLUBBSVC02

    # Check main node 1 (cache/CPU data)
    assert parsed["BLUBBSVC01"]["cpu_pc"] == 1.0
    assert parsed["BLUBBSVC01"]["write_cache_pc"] == 0.0
    assert parsed["BLUBBSVC01"]["total_cache_pc"] == 70.0

    # Check VDisks BLUBBSVC01 (virtual disk data)
    assert parsed["VDisks BLUBBSVC01"]["r_mb"] == 0.0
    assert parsed["VDisks BLUBBSVC01"]["w_mb"] == 0.0
    assert parsed["VDisks BLUBBSVC01"]["r_io"] == 19.0
    assert parsed["VDisks BLUBBSVC01"]["w_io"] == 110.0
    assert parsed["VDisks BLUBBSVC01"]["r_ms"] == 2.0
    assert parsed["VDisks BLUBBSVC01"]["w_ms"] == 0.0

    # Check MDisks BLUBBSVC01 (managed disk data)
    assert parsed["MDisks BLUBBSVC01"]["r_mb"] == 1.0
    assert parsed["MDisks BLUBBSVC01"]["w_mb"] == 16.0
    assert parsed["MDisks BLUBBSVC01"]["r_io"] == 15.0
    assert parsed["MDisks BLUBBSVC01"]["w_io"] == 865.0
    assert parsed["MDisks BLUBBSVC01"]["r_ms"] == 5.0
    assert parsed["MDisks BLUBBSVC01"]["w_ms"] == 1.0

    # Check Drives BLUBBSVC01 (physical drive data)
    assert parsed["Drives BLUBBSVC01"]["r_mb"] == 0.0
    assert parsed["Drives BLUBBSVC01"]["w_mb"] == 0.0
    assert parsed["Drives BLUBBSVC01"]["r_io"] == 0.0
    assert parsed["Drives BLUBBSVC01"]["w_io"] == 0.0
    assert parsed["Drives BLUBBSVC01"]["r_ms"] == 0.0
    assert parsed["Drives BLUBBSVC01"]["w_ms"] == 0.0

    # Check node 2 CPU data
    assert parsed["BLUBBSVC02"]["cpu_pc"] == 1.0


def test_discover_ibm_svc_nodestats_cache(parsed: Mapping[str, Any]) -> None:
    """Test discovery of cache monitoring services."""
    result = list(discover_ibm_svc_nodestats_cache(parsed))

    assert len(result) == 1
    assert ("BLUBBSVC01", None) in result


def test_discover_ibm_svc_nodestats_cpu(parsed: Mapping[str, Any]) -> None:
    """Test discovery of CPU utilization services."""
    result = list(discover_ibm_svc_nodestats_cpu(parsed))

    assert len(result) == 2
    # Check service discovery returns Service objects with item names
    service_items = [service.item for service in result]
    assert "BLUBBSVC01" in service_items
    assert "BLUBBSVC02" in service_items


def test_discover_ibm_svc_nodestats_diskio(parsed: Mapping[str, Any]) -> None:
    """Test discovery of disk I/O monitoring services."""
    result = list(discover_ibm_svc_nodestats_diskio(parsed))

    assert len(result) == 3
    assert ("VDisks BLUBBSVC01", None) in result
    assert ("MDisks BLUBBSVC01", None) in result
    assert ("Drives BLUBBSVC01", None) in result


def test_discover_ibm_svc_nodestats_iops(parsed: Mapping[str, Any]) -> None:
    """Test discovery of IOPS monitoring services."""
    result = list(discover_ibm_svc_nodestats_iops(parsed))

    assert len(result) == 3
    assert ("VDisks BLUBBSVC01", None) in result
    assert ("MDisks BLUBBSVC01", None) in result
    assert ("Drives BLUBBSVC01", None) in result


def test_discover_ibm_svc_nodestats_disk_latency(parsed: Mapping[str, Any]) -> None:
    """Test discovery of disk latency monitoring services."""
    result = list(discover_ibm_svc_nodestats_disk_latency(parsed))

    assert len(result) == 3
    assert ("VDisks BLUBBSVC01", None) in result
    assert ("MDisks BLUBBSVC01", None) in result
    assert ("Drives BLUBBSVC01", None) in result


def test_check_ibm_svc_nodestats_cache(parsed: Mapping[str, Any]) -> None:
    """Test cache usage monitoring."""
    result = check_ibm_svc_nodestats_cache("BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "Write cache usage is 0 %" in result[1]
    assert "total cache usage is 70 %" in result[1]
    assert result[2] == [
        ("write_cache_pc", 0.0, None, None, 0, 100),
        ("total_cache_pc", 70.0, None, None, 0, 100),
    ]


def test_check_ibm_svc_nodestats_cpu(parsed: Mapping[str, Any]) -> None:
    """Test CPU utilization monitoring."""
    params = {"levels": (90.0, 95.0)}
    result = list(check_ibm_svc_nodestats_cpu("BLUBBSVC01", params, parsed))

    assert len(result) == 1
    assert result[0][0] == 0  # OK state (1% < 90%)
    assert "Total CPU: 1.00%" in result[0][1]
    assert result[0][2] == [("util", 1.0, 90.0, 95.0, 0, 100)]

    # Test second node
    result = list(check_ibm_svc_nodestats_cpu("BLUBBSVC02", params, parsed))
    assert len(result) == 1
    assert result[0][0] == 0  # OK state (1% < 90%)
    assert "Total CPU: 1.00%" in result[0][1]
    assert result[0][2] == [("util", 1.0, 90.0, 95.0, 0, 100)]


def test_check_ibm_svc_nodestats_diskio_vdisks(parsed: Mapping[str, Any]) -> None:
    """Test disk I/O monitoring for VDisks."""
    result = check_ibm_svc_nodestats_diskio("VDisks BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "0.00 B/s read, 0.00 B/s write" in result[1]
    assert result[2] == [("read", 0.0), ("write", 0.0)]


def test_check_ibm_svc_nodestats_diskio_mdisks(parsed: Mapping[str, Any]) -> None:
    """Test disk I/O monitoring for MDisks."""
    result = check_ibm_svc_nodestats_diskio("MDisks BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "1.05 MB/s read" in result[1]
    assert "16.8 MB/s write" in result[1]
    assert result[2] == [("read", 1048576.0), ("write", 16777216.0)]


def test_check_ibm_svc_nodestats_diskio_drives(parsed: Mapping[str, Any]) -> None:
    """Test disk I/O monitoring for Drives."""
    result = check_ibm_svc_nodestats_diskio("Drives BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "0.00 B/s read, 0.00 B/s write" in result[1]
    assert result[2] == [("read", 0.0), ("write", 0.0)]


def test_check_ibm_svc_nodestats_iops_vdisks(parsed: Mapping[str, Any]) -> None:
    """Test IOPS monitoring for VDisks."""
    result = check_ibm_svc_nodestats_iops("VDisks BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "19.0 IO/s read, 110.0 IO/s write" in result[1]
    assert result[2] == [("read", 19.0), ("write", 110.0)]


def test_check_ibm_svc_nodestats_iops_mdisks(parsed: Mapping[str, Any]) -> None:
    """Test IOPS monitoring for MDisks."""
    result = check_ibm_svc_nodestats_iops("MDisks BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "15.0 IO/s read, 865.0 IO/s write" in result[1]
    assert result[2] == [("read", 15.0), ("write", 865.0)]


def test_check_ibm_svc_nodestats_iops_drives(parsed: Mapping[str, Any]) -> None:
    """Test IOPS monitoring for Drives."""
    result = check_ibm_svc_nodestats_iops("Drives BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "0.0 IO/s read, 0.0 IO/s write" in result[1]
    assert result[2] == [("read", 0.0), ("write", 0.0)]


def test_check_ibm_svc_nodestats_disk_latency_vdisks(parsed: Mapping[str, Any]) -> None:
    """Test disk latency monitoring for VDisks."""
    result = check_ibm_svc_nodestats_disk_latency("VDisks BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "Latency is 2.0 ms for read, 0.0 ms for write" in result[1]
    assert result[2] == [("read_latency", 2.0), ("write_latency", 0.0)]


def test_check_ibm_svc_nodestats_disk_latency_mdisks(parsed: Mapping[str, Any]) -> None:
    """Test disk latency monitoring for MDisks."""
    result = check_ibm_svc_nodestats_disk_latency("MDisks BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "Latency is 5.0 ms for read, 1.0 ms for write" in result[1]
    assert result[2] == [("read_latency", 5.0), ("write_latency", 1.0)]


def test_check_ibm_svc_nodestats_disk_latency_drives(parsed: Mapping[str, Any]) -> None:
    """Test disk latency monitoring for Drives."""
    result = check_ibm_svc_nodestats_disk_latency("Drives BLUBBSVC01", {}, parsed)

    assert result[0] == 0  # OK state
    assert "Latency is 0.0 ms for read, 0.0 ms for write" in result[1]
    assert result[2] == [("read_latency", 0.0), ("write_latency", 0.0)]


def test_check_ibm_svc_nodestats_missing_items(parsed: Mapping[str, Any]) -> None:
    """Test checks with missing node/service items."""
    # Test missing items return None
    assert check_ibm_svc_nodestats_cache("NonExistentNode", {}, parsed) is None
    assert check_ibm_svc_nodestats_cpu("NonExistentNode", {"levels": (90.0, 95.0)}, parsed) is None
    assert check_ibm_svc_nodestats_diskio("NonExistentService", {}, parsed) is None
    assert check_ibm_svc_nodestats_iops("NonExistentService", {}, parsed) is None
    assert check_ibm_svc_nodestats_disk_latency("NonExistentService", {}, parsed) is None


def test_check_ibm_svc_nodestats_cpu_high_usage() -> None:
    """Test CPU monitoring with high utilization."""
    # Create scenario with high CPU usage
    string_table = [
        ["1", "HIGHCPU", "cpu_pc", "92", "95", "140325134526"],
        ["1", "HIGHCPU", "write_cache_pc", "10", "20", "140325134931"],
        ["1", "HIGHCPU", "total_cache_pc", "85", "90", "140325134716"],
    ]
    parsed = parse_ibm_svc_nodestats(string_table)
    params = {"levels": (90.0, 95.0)}

    result = list(check_ibm_svc_nodestats_cpu("HIGHCPU", params, parsed))
    assert len(result) == 1
    assert result[0][0] == 1  # WARN state (92% > 90%)
    assert "Total CPU: 92.00%" in result[0][1]
    assert result[0][2] == [("util", 92.0, 90.0, 95.0, 0, 100)]


def test_check_ibm_svc_nodestats_cpu_critical_usage() -> None:
    """Test CPU monitoring with critical utilization."""
    # Create scenario with critical CPU usage
    string_table = [
        ["1", "CRITCPU", "cpu_pc", "96", "98", "140325134526"],
        ["1", "CRITCPU", "write_cache_pc", "20", "30", "140325134931"],
        ["1", "CRITCPU", "total_cache_pc", "95", "98", "140325134716"],
    ]
    parsed = parse_ibm_svc_nodestats(string_table)
    params = {"levels": (90.0, 95.0)}

    result = list(check_ibm_svc_nodestats_cpu("CRITCPU", params, parsed))
    assert len(result) == 1
    assert result[0][0] == 2  # CRIT state (96% > 95%)
    assert "Total CPU: 96.00%" in result[0][1]
    assert result[0][2] == [("util", 96.0, 90.0, 95.0, 0, 100)]


def test_parse_ibm_svc_nodestats_invalid_data() -> None:
    """Test parsing with invalid numeric data."""
    string_table = [
        ["1", "NODE1", "cpu_pc", "invalid", "3", "140325134526"],  # Invalid stat_current
        ["1", "NODE1", "write_cache_pc", "50", "60", "140325134931"],
        ["1", "NODE1", "total_cache_pc", "75", "80", "140325134716"],
    ]
    parsed = parse_ibm_svc_nodestats(string_table)

    # Should skip invalid CPU data but keep valid cache data
    assert "cpu_pc" not in parsed.get("NODE1", {})
    assert parsed["NODE1"]["write_cache_pc"] == 50.0
    assert parsed["NODE1"]["total_cache_pc"] == 75.0


def test_parse_ibm_svc_nodestats_decimal_values() -> None:
    """Test parsing with decimal values (newer firmware)."""
    string_table = [
        ["1", "NODE1", "cpu_pc", "15.5", "18.2", "140325134526"],
        ["1", "NODE1", "vdisk_r_ms", "0.216", "0.278", "140325134756"],
        ["1", "NODE1", "vdisk_w_ms", "0.191", "0.455", "140325134931"],
        ["1", "NODE1", "mdisk_r_ms", "0.324", "0.440", "140325134616"],
        ["1", "NODE1", "mdisk_w_ms", "0.393", "0.446", "140325134811"],
    ]
    parsed = parse_ibm_svc_nodestats(string_table)

    # Check decimal parsing
    assert parsed["NODE1"]["cpu_pc"] == 15.5
    assert parsed["VDisks NODE1"]["r_ms"] == 0.216
    assert parsed["VDisks NODE1"]["w_ms"] == 0.191
    assert parsed["MDisks NODE1"]["r_ms"] == 0.324
    assert parsed["MDisks NODE1"]["w_ms"] == 0.393


def test_parse_ibm_svc_nodestats_empty_data() -> None:
    """Test parsing with empty data."""
    parsed = parse_ibm_svc_nodestats([])
    assert parsed == {}


def test_discover_ibm_svc_nodestats_empty_section() -> None:
    """Test discovery with empty section."""
    cache_items = list(discover_ibm_svc_nodestats_cache({}))
    cpu_items = list(discover_ibm_svc_nodestats_cpu({}))
    diskio_items = list(discover_ibm_svc_nodestats_diskio({}))
    iops_items = list(discover_ibm_svc_nodestats_iops({}))
    latency_items = list(discover_ibm_svc_nodestats_disk_latency({}))

    assert len(cache_items) == 0
    assert len(cpu_items) == 0
    assert len(diskio_items) == 0
    assert len(iops_items) == 0
    assert len(latency_items) == 0
