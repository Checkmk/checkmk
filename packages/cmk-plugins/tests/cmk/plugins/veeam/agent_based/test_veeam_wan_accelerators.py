#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import TableRow
from cmk.plugins.veeam.agent_based.veeam_wan_accelerators import (
    inventory_veeam_wan_accelerators,
    parse_veeam_wan_accelerators,
)

_PATH = ["software", "applications", "veeam", "wan_accelerators"]


def _accelerator(name: str, high_bandwidth_mode_enabled: bool) -> list[str]:
    return [
        json.dumps(
            {
                "id": "30e653b9-0f43-457f-b174-f87a389d5e4f",
                "name": name,
                "server": {
                    "hostId": "ea007f36-a093-4f00-b77d-af10e563ce5f",
                    "description": "Created by .\\Administrator at 10/9/2026 5:32 AM.",
                    "trafficPort": 6165,
                    "streamsCount": 5,
                    "highBandwidthModeEnabled": high_bandwidth_mode_enabled,
                },
                "cache": {"cacheSizeUnit": "GB", "cacheFolder": "C:\\VeeamWAN", "cacheSize": 100},
            }
        )
    ]


def _row(name: str, high_bandwidth_mode_enabled: bool) -> TableRow:
    return TableRow(
        path=_PATH,
        key_columns={"name": name},
        inventory_columns={
            "description": "Created by .\\Administrator at 10/9/2026 5:32 AM.",
            "traffic_port": 6165,
            "streams_count": 5,
            "high_bandwidth_mode_enabled": high_bandwidth_mode_enabled,
            "cache_folder": "C:\\VeeamWAN",
            "cache_size": 100_000_000_000,
        },
    )


def test_each_wan_accelerator_is_inventorized_as_a_row() -> None:
    section = parse_veeam_wan_accelerators(
        [_accelerator("wan-01", False), _accelerator("wan-02", True)]
    )

    assert list(inventory_veeam_wan_accelerators(section)) == [
        _row("wan-01", False),
        _row("wan-02", True),
    ]


def test_empty_section_has_no_rows() -> None:
    assert list(inventory_veeam_wan_accelerators(parse_veeam_wan_accelerators([]))) == []
