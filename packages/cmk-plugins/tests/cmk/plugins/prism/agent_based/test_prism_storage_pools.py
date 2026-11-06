#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.prism.agent_based.prism_storage_pools import (
    check_prism_storage_pools,
    discovery_prism_storage_pools,
    parse_prism_storage_pools_v2,
)


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.plugins.prism.agent_based.prism_storage_pools.get_value_store", dict)


SECTION = {
    "StoragePool": {
        "capacity": 41713429587402,
        "ilmDownMigratePctThreshold": 75,
        "markedForRemoval": False,
        "name": "StoragePool",
        "reservedCapacity": 0,
        "tierwiseFreeCapacityMap": None,
        "usageStats": {
            "storage.capacity_bytes": "41713429587402",
            "storage.container_reserved_free_bytes": "0",
            "storage.disk_physical_usage_bytes": "9389790932619",
            "storage.free_bytes": "32360427193802",
            "storage.logical_usage_bytes": "21100952813568",
            "storage.reserved_capacity_bytes": "0",
            "storage.reserved_free_bytes": "0",
            "storage.reserved_usage_bytes": "0",
            "storage.unreserved_capacity_bytes": "41713429587402",
            "storage.unreserved_free_bytes": "32360427193802",
            "storage.unreserved_usage_bytes": "9353002393600",
            "storage.usage_bytes": "9353002393600",
            "storage_tier.das-sata.capacity_bytes": "0",
            "storage_tier.das-sata.free_bytes": "0",
            "storage_tier.das-sata.usage_bytes": "0",
            "storage_tier.ssd.capacity_bytes": "41713429587402",
            "storage_tier.ssd.free_bytes": "32323638654783",
            "storage_tier.ssd.usage_bytes": "9389790932619",
        },
    }
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(item="StoragePool"),
            ],
            id="For every pool, a Service is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discovery_prism_storage_pools(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_storage_pools(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["item", "params", "section", "expected_check_result"],
    [
        pytest.param(
            "StoragePool",
            FILESYSTEM_DEFAULT_PARAMS,
            SECTION,
            [
                Metric(
                    "fs_used",
                    8919718.1640625,
                    levels=(31824821.157380104, 35802923.8020525),
                    boundaries=(0.0, 39781026.446725845),
                ),
                Metric("fs_free", 30861308.282663345, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    22.422041261322537,
                    levels=(79.99999999999856, 89.99999999999808),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 22.42% - 8.51 TiB of 37.9 TiB"),
                Metric("fs_size", 39781026.446725845, boundaries=(0.0, None)),
                Result(state=State.OK, summary="SSD capacity: 37.9 TiB, SSD free: 29.4 TiB"),
            ],
            id="If the disk is in expected mount state and healthy, the check result is OK.",
        ),
    ],
)
@pytest.mark.usefixtures("empty_value_store")
def test_check_prism_storage_pools(  # type: ignore[misc]
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_storage_pools(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )


# What the v4 agent writes for the storage pool recorded on a Prism Central 7.5 lab: its 18 disks
RECORDED_V4_SECTION = [
    [
        (
            Path(__file__).parent.parent
            / "special_agent"
            / "v4_fixtures"
            / "section_prism_storage_pools_v2.json"
        ).read_text()
    ]
]


def _v4_pool(*disks: tuple[str, int, int]) -> StringTable:
    """One pool with a disk per (storage tier, capacity, free bytes)"""

    def series(value: int) -> list[dict[str, object]]:
        return [{"value": value, "timestamp": "2026-11-05T09:09:30Z"}]

    return [
        [
            json.dumps(
                [
                    {
                        "extId": "64b62dc3-b8a9-47c1-9026-3af2009d231e",
                        "disks": [
                            {
                                "storageTier": tier,
                                "stats": {
                                    "diskCapacityBytes": series(capacity),
                                    "diskFreeBytes": series(free),
                                },
                            }
                            for tier, capacity, free in disks
                        ],
                    }
                ]
            )
        ]
    ]


def _v4_results(section: Mapping[str, Any]) -> list[Result]:
    return [
        result
        for result in check_prism_storage_pools(
            item="64b62dc3", params=FILESYSTEM_DEFAULT_PARAMS, section=section
        )
        if isinstance(result, Result)
    ]


def test_v4_pool_is_discovered_by_the_start_of_its_id() -> None:
    section = parse_prism_storage_pools_v2(RECORDED_V4_SECTION)

    assert list(discovery_prism_storage_pools(section)) == [Service(item="64b62dc3")]


@pytest.mark.usefixtures("empty_value_store")
def test_v4_pool_shows_the_sum_of_its_disks() -> None:
    section = parse_prism_storage_pools_v2(RECORDED_V4_SECTION)

    assert _v4_results(section) == [
        Result(state=State.OK, summary="Used: 14.35% - 8.39 TiB of 58.5 TiB"),
        Result(state=State.OK, summary="SSD capacity: 58.5 TiB, SSD free: 50.1 TiB"),
    ]


@pytest.mark.usefixtures("empty_value_store")
def test_v4_pool_shows_each_tier_and_counts_other_tiers_only_in_the_total() -> None:
    section = parse_prism_storage_pools_v2(
        _v4_pool(
            ("SSD_SATA", 4 * 1024**4, 3 * 1024**4),
            ("DAS_SATA", 8 * 1024**4, 2 * 1024**4),
            ("HDD", 4 * 1024**4, 3 * 1024**4),
        )
    )

    assert _v4_results(section) == [
        Result(state=State.OK, summary="Used: 50.00% - 8.00 TiB of 16.0 TiB"),
        Result(state=State.OK, summary="SAS/SATA capacity: 8.00 TiB, SAS/SATA free: 2.00 TiB"),
        Result(state=State.OK, summary="SSD capacity: 4.00 TiB, SSD free: 3.00 TiB"),
    ]
