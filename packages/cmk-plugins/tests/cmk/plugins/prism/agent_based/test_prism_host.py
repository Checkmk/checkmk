#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.prism.agent_based.prism_host import parse_prism_host_v2
from cmk.plugins.prism.agent_based.prism_host_disks import discovery_prism_host_disks
from cmk.plugins.prism.agent_based.prism_host_stats import discovery_prism_host_stats

RECORDED_SECTION = (
    Path(__file__).parent.parent / "special_agent" / "v4_fixtures" / "section_prism_host_v2.json"
)


def _parse(node: object) -> dict[str, object]:
    return parse_prism_host_v2([[json.dumps(node)]])


def _sample(value: int) -> list[dict[str, object]]:
    return [{"value": value, "timestamp": "2026-11-04T07:14:30Z"}]


def _disk(
    location: int, tier: str, capacity: int, free: int, advance: dict[str, bool]
) -> dict[str, object]:
    return {
        "config": {
            "location": location,
            "model": "KIOXIA",
            "serialNumber": f"SERIAL{location}",
            "storageTier": tier,
            "diskAdvanceConfig": advance,
        },
        "stats": {"diskCapacityBytes": _sample(capacity), "diskFreeBytes": _sample(free)},
    }


def test_recorded_v4_node_gives_the_legacy_section() -> None:
    """Recorded on the lab together with the legacy API, which answered the same, except
    hypervisor_memory_usage_ppm 391686 (v4 has no field that matches it exactly) and the disks:
    for these NVMe disks the legacy API reports none"""
    serials = {4096: 13, 4097: 14, 4098: 15, 4099: 16, 4100: 17, 4101: 18}

    assert _parse(json.loads(RECORDED_SECTION.read_text())) == {
        "num_cpu_sockets": 2,
        "num_cpu_cores": 64,
        "num_cpu_threads": 128,
        "memory_capacity_in_bytes": 1622495199232,
        "cpu_capacity_in_hz": 246016000000,
        "stats": {
            "controller_avg_io_latency_usecs": "802",
            "controller_avg_read_io_latency_usecs": "0",
            "controller_avg_write_io_latency_usecs": "802",
            "hypervisor_cpu_usage_ppm": "520557",
            "hypervisor_memory_usage_ppm": "396449",
            "controller_avg_read_io_size_kbytes": "0",
            "controller_avg_write_io_size_kbytes": "9",
        },
        "usage_stats": {
            "storage.capacity_bytes": "21426395490720",
            "storage.free_bytes": "20333374919675",
            "storage_tier.ssd.capacity_bytes": "21426395490720",
            "storage_tier.ssd.free_bytes": "20333374919675",
            "storage_tier.das-sata.capacity_bytes": "0",
            "storage_tier.das-sata.free_bytes": "0",
        },
        "disk_hardware_configs": {
            str(location): {
                "bad": False,
                "model": "KIOXIA KCD8XRUG3T84",
                "serial_number": f"DISKSERIAL{serial}",
                "mounted": True,
            }
            for location, serial in serials.items()
        },
    }


def test_idle_node_is_discovered_like_with_the_legacy_api() -> None:
    section = _parse(
        {
            "config": {},
            "stats": {"controllerAvgIoLatencyUsecs": _sample(0)},
        }
    )

    assert list(discovery_prism_host_stats(section)) == [Service()]


def test_stats_v4_does_not_report_are_unknown_like_with_the_legacy_api() -> None:
    section = _parse({"config": {}, "stats": {}})

    assert (section["stats"], section["usage_stats"]) == (
        dict.fromkeys(
            (
                "controller_avg_io_latency_usecs",
                "controller_avg_read_io_latency_usecs",
                "controller_avg_write_io_latency_usecs",
                "hypervisor_cpu_usage_ppm",
                "hypervisor_memory_usage_ppm",
                "controller_avg_read_io_size_kbytes",
                "controller_avg_write_io_size_kbytes",
            ),
            "-1",
        ),
        {
            "storage.capacity_bytes": "-1",
            "storage.free_bytes": "-1",
            "storage_tier.ssd.capacity_bytes": "0",
            "storage_tier.ssd.free_bytes": "0",
            "storage_tier.das-sata.capacity_bytes": "0",
            "storage_tier.das-sata.free_bytes": "0",
        },
    )


def test_disks_count_into_their_tier() -> None:
    mounted = {"isMounted": True}
    section = _parse(
        {
            "config": {},
            "stats": {},
            "disks": [
                _disk(1, "SSD_SATA", 100, 40, mounted),
                _disk(2, "SSD_PCIE", 200, 50, mounted),
                _disk(3, "DAS_SATA", 1000, 600, mounted),
            ],
        }
    )

    assert section["usage_stats"] == {
        "storage.capacity_bytes": "-1",
        "storage.free_bytes": "-1",
        "storage_tier.ssd.capacity_bytes": "300",
        "storage_tier.ssd.free_bytes": "90",
        "storage_tier.das-sata.capacity_bytes": "1000",
        "storage_tier.das-sata.free_bytes": "600",
    }


@pytest.mark.parametrize(
    ["advance_config", "bad"],
    [
        pytest.param({"isUnhealthy": True}, True, id="unhealthy"),
        pytest.param({"isUnhealthy": False}, False, id="healthy"),
        pytest.param({}, False, id="no flag"),
    ],
)
def test_disk_is_bad_only_if_flagged_unhealthy(advance_config: dict[str, bool], bad: bool) -> None:
    section = _parse(
        {
            "config": {},
            "stats": {},
            "disks": [_disk(1, "SSD_SATA", 1, 1, {**advance_config, "isMounted": False})],
        }
    )

    assert section["disk_hardware_configs"] == {
        "1": {"bad": bad, "model": "KIOXIA", "serial_number": "SERIAL1", "mounted": False}
    }


def test_disk_without_mount_state_is_not_discovered() -> None:
    section = _parse(
        {"config": {}, "stats": {}, "disks": [_disk(1, "SSD_SATA", 1, 1, {"isUnhealthy": True})]}
    )

    assert list(discovery_prism_host_disks(section)) == []
