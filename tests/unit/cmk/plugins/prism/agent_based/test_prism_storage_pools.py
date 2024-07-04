#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.prism.agent_based.prism_storage_pools import (
    check_prism_storage_pools,
    discovery_prism_storage_pools,
)

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
def test_discovery_prism_storage_pools(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_storage_pools(section)) == expected_discovery_result


@pytest.mark.usefixtures("initialised_item_state")
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
def test_check_prism_storage_pools(
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
