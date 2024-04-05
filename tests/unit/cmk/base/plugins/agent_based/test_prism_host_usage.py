#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.prism_host_usage import (
    check_prism_host_usage,
    discovery_prism_host_usage,
)

from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

SECTION = {
    "state": "NORMAL",
    "usage_stats": {
        "storage.capacity_bytes": "13904476529134",
        "storage.free_bytes": "10915468123981",
        "storage.logical_usage_bytes": "6816119521280",
        "storage.usage_bytes": "2989008405153",
        "storage_tier.das-sata.capacity_bytes": "0",
        "storage_tier.das-sata.free_bytes": "0",
        "storage_tier.das-sata.usage_bytes": "0",
        "storage_tier.ssd.capacity_bytes": "13904476529134",
        "storage_tier.ssd.free_bytes": "10915468123981",
        "storage_tier.ssd.usage_bytes": "2989008405153",
    },
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(item="Capacity"),
            ],
            id="One check is discovered if the host provides usage data.",
        ),
        pytest.param(
            {"state": "NORMAL"},
            [],
            id="If there is no usage data, nothing is discovered.",
        ),
    ],
)
def test_discovery_prism_host_usage(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_host_usage(section)) == expected_discovery_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["item", "params", "section", "expected_check_result"],
    [
        pytest.param(
            "Capacity",
            FILESYSTEM_DEFAULT_PARAMS,
            SECTION,
            [
                Metric(
                    "fs_used",
                    2850540.547516823,
                    levels=(10608273.719126701, 11934307.934017181),
                    boundaries=(0.0, 13260342.148908615),
                ),
                Metric("fs_free", 10409801.601391792, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    21.49673451488908,
                    levels=(79.99999999999856, 89.99999999999568),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 21.50% - 2.99 TB of 13.9 TB"),
                Metric("fs_size", 13260342.148908615, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Total SAS: 0 B, Free SAS: 0 B"),
                Result(state=State.OK, summary="Total SSD: 13.9 TB, Free SSD: 10.9 TB"),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_host_usage(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_host_usage(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
