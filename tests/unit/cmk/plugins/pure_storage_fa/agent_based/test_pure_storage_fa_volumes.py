#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.pure_storage_fa.agent_based.pure_storage_fa_volumes import (
    check_volume_capacity,
    discover_volume_capacity,
    parse_volume,
    Volume,
)

VOLUMES = {
    "TestVol1": Volume(
        virtual=3820131840.0,
        total_provisioned=107374182400.0,
        data_reduction=8.522708060028126,
        unique=447850921.0,
        snapshots=2890766.0,
    )
}


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            [
                [
                    '{"continuation_token": null, "items": [{"connection_count": 1, "created": 1685140173991, "destroyed": false, "host_encryption_key_status": "none", "id": "66a46ff1-3d06-a594-d839-0b28bbf84e64", "name": "TestVol1", "pod": {"id": null, "name": null}, "promotion_status": "promoted", "provisioned": 107374182400, "qos": {"bandwidth_limit": null, "iops_limit": null}, "requested_promotion_state": "promoted", "serial": "C140B842715A410400011010", "source": {"id": null, "name": null}, "space": {"data_reduction": 8.522708060028126, "shared": null, "snapshots": 2890766, "system": null, "thin_provisioning": 0.9644222497940064, "total_physical": 450741687, "total_provisioned": 107374182400, "total_reduction": 239.55163018127936, "unique": 447850921, "virtual": 3820131840}, "subtype": "regular", "time_remaining": null, "volume_group": {"id": null, "name": null}}], "more_items_remaining": false, "total": [{"connection_count": null, "created": null, "destroyed": null, "host_encryption_key_status": null, "id": null, "name": null, "pod": {"id": null, "name": null}, "promotion_status": null, "provisioned": 107374182400, "qos": {"bandwidth_limit": null, "iops_limit": null}, "requested_promotion_state": null, "serial": null, "source": {"id": null, "name": null}, "space": {"data_reduction": 8.522708060028126, "shared": null, "snapshots": 2890766, "system": null, "thin_provisioning": 0.9644222497940064, "total_physical": 450741687, "total_provisioned": 107374182400, "total_reduction": 239.55163018127936, "unique": 447850921, "virtual": 3820131840}, "subtype": null, "time_remaining": null, "volume_group": {"id": null, "name": null}}], "total_item_count": null}'
                ]
            ],
            VOLUMES,
            id="one volume in section",
        ),
        pytest.param(
            [
                [
                    '{"continuation_token": null, "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            None,
            id="no volumes",
        ),
    ],
)
def test_parse_volume(string_table: StringTable, expected_section: Mapping[str, Volume]) -> None:
    assert parse_volume(string_table) == expected_section


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            VOLUMES,
            [Service(item="TestVol1")],
        )
    ],
)
def test_discover_volume_capacity(
    section: Mapping[str, Volume], expected_services: DiscoveryResult
) -> None:
    assert list(discover_volume_capacity(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            VOLUMES,
            "TestVol1",
            {"levels": (80.0, 90.0), "levels_low": (50.0, 60.0), "magic_normsize": 20},
            [
                Metric(
                    "fs_used",
                    3643.16162109375,
                    levels=(81920.0, 92160.0),
                    boundaries=(0.0, 102400.0),
                ),
                Metric("fs_free", 98756.83837890625, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    3.5577750205993652,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 3.56% - 3.56 GiB of 100 GiB"),
                Result(state=State.OK, summary="Data reduction: 8.52 to 1"),
                Metric("data_reduction", 8.522708060028126),
                Result(state=State.OK, notice="Size: 100 GiB"),
                Metric("fs_size", 107374182400.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Physical capacity used - volume: 427 MiB"),
                Metric("unique_size", 447850921.0),
                Result(state=State.OK, notice="Physical capacity used - snapshots: 2.76 MiB"),
                Metric("snapshots_size", 2890766.0),
                Result(state=State.OK, notice="Virtual capacity used - volume: 3.56 GiB"),
                Metric("virtual_size", 3820131840.0),
            ],
            id="item present in section",
        ),
        pytest.param(
            VOLUMES,
            "Unknown",
            {"levels": (80.0, 90.0), "levels_low": (50.0, 60.0), "magic_normsize": 20},
            [],
            id="no item in section",
        ),
    ],
)
def test_check_volume_capacity(
    section: Mapping[str, Volume],
    item: str,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    assert list(check_volume_capacity(item, params, section)) == expected_result
