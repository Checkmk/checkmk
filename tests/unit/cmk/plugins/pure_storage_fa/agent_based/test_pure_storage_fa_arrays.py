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
from cmk.plugins.pure_storage_fa.agent_based.pure_storage_fa_arrays import (
    Array,
    check_overall_capacity,
    discover_overall_capacity,
    parse_array,
)

ARRAY = Array(
    total_physical=457340865.0,
    capacity=257315517236.0,
    data_reduction=8.40809655446072,
    unique=447850990.0,
    snapshots=2890766.0,
    shared=6599109.0,
    system=0.0,
    replication=0.0,
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            [
                [
                    '{"continuation_token": null, "items": [{"banner": "", "capacity": 257315517236, "console_lock_enabled": false, "encryption": {"data_at_rest": {"algorithm": "AES-256-CTR", "enabled": true}, "module_version": "FA-1.3"}, "eradication_config": {"eradication_delay": 86400000}, "id": "c140b842-715a-4104-a0ca-d05b1a61d1cd", "idle_timeout": 1800000, "name": "pod-46-vfa", "ntp_servers": ["time1.purestorage.com", "time2.purestorage.com", "time3.purestorage.com"], "os": "Purity//FA", "parity": 1.0, "scsi_timeout": 60000, "space": {"data_reduction": 8.40809655446072, "replication": 0, "shared": 6599109, "snapshots": 2890766, "system": 0, "thin_provisioning": 0.9644222497940064, "total_physical": 457340865, "total_provisioned": null, "total_reduction": 236.33016081309762, "unique": 447850990, "virtual": 3820131840}, "version": "6.1.24"}], "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            ARRAY,
            id="one array in section",
        ),
        pytest.param(
            [
                [
                    '{"continuation_token": null, "items": [], "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            None,
            id="no arrays",
        ),
    ],
)
def test_parse_array(string_table: StringTable, expected_section: Array) -> None:
    assert parse_array(string_table) == expected_section


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            ARRAY,
            [Service(item="Overall")],
        )
    ],
)
def test_discover_overall_capacity(section: Array, expected_services: DiscoveryResult) -> None:
    assert list(discover_overall_capacity(section)) == expected_services


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            ARRAY,
            "Overall",
            {"levels": (80.0, 90.0), "levels_low": (50.0, 60.0), "magic_normsize": 20},
            [
                Metric(
                    "fs_used",
                    436.15423679351807,
                    levels=(196316.1599998474, 220855.68000030518),
                    boundaries=(0.0, 245395.20000076294),
                ),
                Metric("fs_free", 244959.04576396942, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    0.17773543932080255,
                    levels=(79.9999999996891, 89.99999999984455),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 0.18% - 436 MiB of 240 GiB"),
                Metric("fs_size", 257315517236.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Data reduction: 8.41 to 1"),
                Metric("data_reduction", 8.40809655446072),
                Result(state=State.OK, notice="Unique: 427 MiB"),
                Metric("unique_size", 447850990.0),
                Result(state=State.OK, notice="Snapshots: 2.76 MiB"),
                Metric("snapshots_size", 2890766.0),
                Result(state=State.OK, notice="Shared: 6.29 MiB"),
                Metric("shared_size", 6599109.0),
                Result(state=State.OK, notice="System: 0 B"),
                Metric("system_size", 0.0),
                Result(state=State.OK, notice="Replication: 0 B"),
                Metric("replication_size", 0.0),
                Result(state=State.OK, notice="Empty: 239 GiB"),
            ],
        )
    ],
)
def test_check_overall_capacity(
    section: Array, item: str, params: Mapping[str, Any], expected_result: CheckResult
) -> None:
    assert list(check_overall_capacity(item, params, section)) == expected_result
